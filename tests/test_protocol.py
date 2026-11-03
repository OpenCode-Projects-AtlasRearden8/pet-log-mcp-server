"""JSON-RPC / MCP protocol tests using handle_request with a fake store."""

import json

from pet_log_mcp import __version__
from pet_log_mcp.server import (
    JSONRPC_ERROR_INVALID_PARAMS,
    JSONRPC_ERROR_INVALID_REQUEST,
    JSONRPC_ERROR_METHOD_NOT_FOUND,
    JSONRPC_ERROR_PARSE,
    handle_request,
)
from pet_log_mcp.store import JsonStore
from pet_log_mcp.tools import TOOLS

from conftest import FakeStore


def rpc(fake_store, method, params=None, request_id=1, raw=None):
    request = raw if raw is not None else {
        "jsonrpc": "2.0",
        "method": method,
        **({"params": params} if params is not None else {}),
        **({} if request_id is None else {"id": request_id}),
    }
    return handle_request(request, fake_store)


def test_initialize_returns_protocol_and_server_info(fake_store):
    resp = rpc(fake_store, "initialize", {})
    assert resp["id"] == 1
    result = resp["result"]
    assert result["protocolVersion"]
    assert "tools" in result["capabilities"]
    assert result["serverInfo"]["version"] == __version__


def test_initialized_notification_returns_none(fake_store):
    assert rpc(fake_store, "notifications/initialized", {}, request_id=None) is None


def test_ping_notification_and_request(fake_store):
    assert rpc(fake_store, "ping", {}, request_id=None) is None
    request = {"jsonrpc": "2.0", "id": 7, "method": "ping"}
    assert handle_request(request, fake_store) == {"jsonrpc": "2.0", "id": 7}


def test_tools_list_matches_registry(fake_store):
    result = rpc(fake_store, "tools/list")["result"]
    names = [t["name"] for t in result["tools"]]
    assert names == list(TOOLS)
    for tool in result["tools"]:
        assert tool["title"]
        assert tool["description"]
        assert tool["inputSchema"]["type"] == "object"


def test_tools_call_success_returns_content(fake_store):
    result = rpc(
        fake_store,
        "tools/call",
        {"name": "add_pet", "arguments": {"name": "Mochi", "species": "cat"}},
    )["result"]
    assert result["isError"] is False
    assert "Mochi" in result["content"][0]["text"]


def test_tools_call_tool_error_sets_is_error(fake_store):
    result = rpc(fake_store, "tools/call", {"name": "add_pet", "arguments": {}})["result"]
    assert result["isError"] is True
    assert "name" in result["content"][0]["text"]


def test_tools_call_unknown_tool_is_protocol_error(fake_store):
    resp = rpc(fake_store, "tools/call", {"name": "no_such_tool", "arguments": {}})
    assert resp["error"]["code"] == JSONRPC_ERROR_INVALID_PARAMS


def test_method_not_found(fake_store):
    resp = rpc(fake_store, "history/hello")
    assert resp["error"]["code"] == JSONRPC_ERROR_METHOD_NOT_FOUND


def test_invalid_jsonrpc_envelope(fake_store):
    resp = rpc(fake_store, None, raw={"id": 1, "method": "ping"})
    assert resp["error"]["code"] == JSONRPC_ERROR_INVALID_REQUEST


def test_broken_arguments_type(fake_store):
    resp = rpc(fake_store, "tools/call", {"name": "list_pets", "arguments": "nope"})
    assert resp["error"]["code"] == JSONRPC_ERROR_INVALID_PARAMS


def test_notification_of_tools_call_gets_no_response(fake_store):
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "add_pet", "arguments": {"name": "Mochi"}},
    }
    assert handle_request(request, fake_store) is None


def test_real_store_writes_through_tools_call(tmp_path):
    store = JsonStore(tmp_path)
    request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "add_pet", "arguments": {"name": "Mochi"}},
    }
    result = handle_request(request, store)["result"]
    assert result["isError"] is False
    on_disk = json.loads((tmp_path / "pets.json").read_text(encoding="utf-8"))
    assert on_disk[0]["name"] == "Mochi"
