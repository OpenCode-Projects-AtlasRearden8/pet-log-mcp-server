# Pet Log MCP Server

A local MCP server for household pet care notes: vet-visit histories, medication
organizers, weight trends, feeding notes, and on-demand groomer/sitter handoff
summaries. Plain Python, standard library only, JSON-RPC over stdio — exactly
what an MCP client expects. **No network calls, ever.**

> **Education and organizing only.** This tool is a notebook, not a vet. It
> stores and summarizes *your own* notes; it never gives medical, medication
> dosing, or feeding advice. Always consult your veterinarian for medical
> decisions.

Made by [Asdale Dynamics, LLC](https://dylanasdale.github.io) — plain-English AI
education and practical local-first tools. Licensed MIT.

## Why this exists

The companion project `new-pet-first-week-guide` is the setup manual for a pet's
first days home. This project is the **ongoing log**: the place where the
checkup records, medication schedules the vet gave you (organized by you,
corrected by you), weigh-ins from your own scale, food notes, and hand-off
notes for the groomer or pet sitter live for the long haul.

## How it works

- **One JSON folder you own.** All data lives in six plain-JSON files
  (`pets.json`, `vet_visits.json`, `medications.json`, `weights.json`,
  `feeding_notes.json`, `handoff_notes.json`) in a single folder. Open it,
  read it, back it up, keep it in your own cloud drive if you like.
- **MCP-style stdio server.** Speaks JSON-RPC 2.0 (the same shape the Model
  Context Protocol uses) with `initialize`, `notifications/initialized`,
  `ping`, `tools/list`, and `tools/call`. One JSON message per line on stdin,
  one response per line on stdout; log messages go to stderr only.
- **Zero dependencies at runtime.** Python 3.10+ standard library only.
  `pytest` is a test-time dependency only.

## Tools (13)

| Tool | Purpose |
| --- | --- |
| `add_pet`, `list_pets` | Register and list the pets in the log. |
| `add_vet_visit`, `list_vet_visits` | Build a per-pet vet-visit history. |
| `add_medication`, `list_medications` | Organize the schedules your vet gave you (never dosing advice). |
| `add_weight`, `weight_trend` | Record weigh-ins and see the trend with per-entry change. |
| `add_feeding_note`, `list_feeding_notes` | Log feeding observations, newest first. |
| `add_handoff_note`, `get_handoff_summary` | Groomer/sitter hand-off summaries, assembled on demand. |
| `delete_record` | Remove one wrong or duplicated record by id. |

## Quick start

Run the server directly (no install needed, from the repo folder):

```bash
python -m pet_log_mcp
```

Name the data folder explicitly (default is `./pet-log-data`):

```bash
PET_LOG_DATA_DIR=/home/you/pet-logs python -m pet_log_mcp
```

Or install it with pip to get the `pet-log-mcp` command:

```bash
pip install .
```

### Manual smoke test

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"add_pet","arguments":{"name":"Mochi","species":"cat"}}}' \
  | python -m pet_log_mcp
```

### Wiring it into an MCP client

Point your MCP client at the process `python -m pet_log_mcp` (transport:
stdio, no args). If the client app stores `mcpServers` config, a local-first
example looks like:

```json
{
  "mcpServers": {
    "pet-log": {
      "command": "python",
      "args": ["-m", "pet_log_mcp"]
    }
  }
}
```

Set `PET_LOG_DATA_DIR` in the environment (or add an `"env"` block, if your
client supports it) to keep the JSON folder wherever you keep personal data.

## Tests

```bash
python -m pytest
```

The test suite covers the store, every tool (through mocked/fake persistence),
the full JSON-RPC protocol surface, and a subprocess end-to-end run of the real
stdio server. No test touches the network.

## Privacy, first and always

- Everything stays in the local JSON folder. Nothing is sent anywhere.
- No telemetry, no analytics, no embedded API keys, no commitments.
- Because it's your data: adding a pet's name in the log is on you; the file
  format is plain JSON so you can edit or export anytime.

## Disclaimer

Pet Log MCP Server is an organizing and education tool. It does not provide
veterinary diagnosis, treatment, dosing, or feeding recommendations and must
not be used as a substitute for professional veterinary care.

## License

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 Asdale Dynamics, LLC.
