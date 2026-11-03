"""Minimal MCP-style JSON-RPC 2.0 server over stdio (stdlib only).

Speaks the core surface of the Model Context Protocol:
  initialize, notifications/initialized, ping, tools/list, tools/call.

Transport: one JSON-RPC message per line on stdin; responses (one per line)
go to stdout. Nothing touches the network. Logs go to stderr only.
"""

import json
import sys
from pathlib import Path

from .store import JsonStore
from .tools import TOOLS, ToolError

__version__ = "1.0.0"

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {
    "name": "pet-log-mcp-server",
    "title": "Pet Log MCP Server",
    "version": __version__,
}

JSONRPC_ERROR_PARSE = -32700
JSONRPC_ERROR_INVALID_REQUEST = -32600
JSONRPC_ERROR_METHOD_NOT_FOUND = -32601
JSONRPC_ERROR_INVALID_PARAMS = -32602
JSONRPC_ERROR_INTERNAL = -32603


def _make_error(code: int, message: str, request_id=None) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def _notify_or_error(is_notification: bool, request_id, code: int, message: str):
    if is_notification:
        return None
    return _make_error(code, message, request_id)


def _tools_list_payload() -> dict:
    return {
        "tools": [
            {
                "name": name,
                "title": spec["title"],
                "description": spec["description"],
                "inputSchema": spec["inputSchema"],
            }
            for name, spec in TOOLS.items()
        ]
    }


def handle_request(request: dict, store: JsonStore) -> dict | None:
    """Handle a decoded JSON-RPC request; return a response dict or None."""
    if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
        return _make_error(
            JSONRPC_ERROR_INVALID_REQUEST, "Invalid JSON-RPC request.", None
        )
    method = request.get("method")
    request_id = request.get("id")
    is_notification = "id" not in request

    def notify() -> dict | None:
        if is_notification:
            return None
        return {"jsonrpc": "2.0", "id": request_id}

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            },
        }
    if method == "notifications/initialized":
        return None
    if method == "ping":
        return notify()
    if method == "tools/list":
        if is_notification:
            return None
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": _tools_list_payload(),
        }
    if method == "tools/call":
        params = request.get("params") or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}
        spec = TOOLS.get(name)
        if spec is None:
            return _notify_or_error(
                is_notification, request_id,
                JSONRPC_ERROR_INVALID_PARAMS, f"Unknown tool: {name!r}",
            )
        if not isinstance(arguments, dict):
            return _notify_or_error(
                is_notification, request_id,
                JSONRPC_ERROR_INVALID_PARAMS, "arguments must be an object.",
            )
        try:
            text = spec["handler"](store, arguments)
        except ToolError as exc:
            result = {"content": [{"type": "text", "text": str(exc)}], "isError": True}
        except Exception as exc:
            print(f"[pet-log-mcp] tool error: {exc!r}", file=sys.stderr)
            return _notify_or_error(
                is_notification, request_id,
                JSONRPC_ERROR_INTERNAL, f"Internal error: {exc}",
            )
        else:
            result = {"content": [{"type": "text", "text": text}], "isError": False}
        if is_notification:
            return None
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    return _make_error(
        JSONRPC_ERROR_METHOD_NOT_FOUND,
        f"Method not found: {method!r}",
        request_id,
    )


def serve(
    stdin=None,
    stdout=None,
    data_dir: Path | str | None = None,
) -> None:
    """Run the stdio loop until stdin is closed."""
    input_stream = stdin if stdin is not None else sys.stdin
    output_stream = stdout if stdout is not None else sys.stdout
    store = JsonStore(data_dir) if data_dir else JsonStore()
    for line in input_stream:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            response = _make_error(JSONRPC_ERROR_PARSE, f"Parse error: {exc}", None)
        else:
            response = handle_request(request, store)
        if response is not None:
            output_stream.write(json.dumps(response) + "\n")
            output_stream.flush()


def main() -> None:
    print(f"[pet-log-mcp] {SERVER_INFO['name']} v{__version__} ready on stdio", file=sys.stderr)
    serve()


if __name__ == "__main__":
    main()
