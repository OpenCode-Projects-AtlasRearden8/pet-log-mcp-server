"""End-to-end tests: run the real stdio server as a subprocess.

These prove the zero-network claim: stdin/stdout only, one JSON-RPC message
per line, exit code 0 when stdin closes.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

SERVER_MODULE = [sys.executable, "-m", "pet_log_mcp"]


def run_server(lines: list[str], data_dir: Path) -> tuple[list[dict], int, str]:
    env = dict(os.environ)
    env["PET_LOG_DATA_DIR"] = str(data_dir)
    proc = subprocess.run(
        SERVER_MODULE,
        input="\n".join(lines) + "\n",
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        check=False,
    )
    output = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    return output, proc.returncode, proc.stderr


def test_full_session_initialize_to_tool_call(tmp_path):
    responses, code, stderr = run_server(
        [
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
            json.dumps({
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "add_pet", "arguments": {"name": "Mochi", "species": "cat"}},
            }),
            json.dumps({
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "get_handoff_summary",
                    "arguments": {"pet_name": "Mochi", "audience": "sitter"},
                },
            }),
        ],
        tmp_path,
    )
    assert code == 0
    # notifications produce no response, so we expect four lines
    ids = [r.get("id") for r in responses]
    assert ids == [1, 2, 3, 4]
    assert responses[0]["result"]["serverInfo"]["name"] == "pet-log-mcp-server"
    tool_names = {t["name"] for t in responses[1]["result"]["tools"]}
    assert {"add_pet", "get_handoff_summary", "weight_trend"} <= tool_names
    assert responses[2]["result"]["isError"] is False
    assert "Mochi" in responses[3]["result"]["content"][0]["text"]
    assert "pet-log-mcp" in stderr  # logs go to stderr, never stdout
    assert json.loads((tmp_path / "pets.json").read_text(encoding="utf-8"))


def test_parse_error_and_method_not_found(tmp_path):
    responses, code, _ = run_server(
        [
            "this is not json",
            json.dumps({"jsonrpc": "2.0", "id": 9, "method": "missing/method"}),
        ],
        tmp_path,
    )
    assert code == 0
    assert responses[0]["error"]["code"] == -32700
    assert responses[1]["error"]["code"] == -32601
