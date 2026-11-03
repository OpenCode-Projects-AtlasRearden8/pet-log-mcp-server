# STATUS.md — Pet Log MCP Server

Last updated: 2026-11-03

## What was built

A local-only MCP server (JSON-RPC 2.0 over stdio) that organizes household
pet-care notes. It is the ongoing-log companion to an adoption/first-week
setup guide:

- **pet_log_mcp/store.py** — per-collection JSON storage in one folder
  (`pets.json`, `vet_visits.json`, `medications.json`, `weights.json`,
  `feeding_notes.json`, `handoff_notes.json`), atomic writes
  (temp file + `os.replace`), case-insensitive pet lookups.
- **pet_log_mcp/tools.py** — 13 tools with education disclaimer messaging:
  add/list pets; log/list vet-visit history; add/list medication schedules
  (organizer for the vet's own instructions — never dosing advice);
  log weights (kg/lb) and show the trend with per-entry change;
  add/list feeding notes (newest first, limit); add groomer/sitter/vet-tech/
  family handoff notes and assemble an on-demand handoff summary;
  delete any record by id.
- **pet_log_mcp/server.py** — minimal MCP-surface stdio server:
  `initialize`, `notifications/initialized`, `ping`, `tools/list`,
  `tools/call`, with correct notification behavior (no responses), proper
  JSON-RPC error codes (-32700/-32600/-32601/-32602/-32603), tool errors
  surfaced as `isError: true` results, logs to stderr only.
- **tests/** — 41 tests: store behavior, every tool through a fake
  (in-memory) store, the JSON-RPC protocol surface, and subprocess
  end-to-end runs of the real stdio server.
- **Docs/meta** — README with quick start and MCP-client wiring, MIT
  LICENSE (Copyright (c) 2026 Asdale Dynamics, LLC), pyproject.toml
  (zero runtime dependencies; `pytest` only for dev/test), .gitignore.

## How to run

```bash
python -m pet_log_mcp
# optional: PET_LOG_DATA_DIR=/path/to/folder python -m pet_log_mcp
```

Data lands in `./pet-log-data` (or the `PET_LOG_DATA_DIR` folder) as plain
JSON. Installable via `pip install .`, which also provides the
`pet-log-mcp` console command.

## Verification results (2026-11-03)

- `python -m pytest` → **41 passed**.
- `pip install --target <tmp> .` → succeeded (wheel build OK; removed the
  PEP 639-deprecated license classifier that broke it the first pass).
- Manual stdio smoke session: initialize → add pet → 2 weigh-ins →
  weight trend (+0.35 kg delta shown) → medication → groomer handoff
  summary — all responses correct on stdout; writes verified in the JSON
  folder; no response emitted for notifications or blank lines.
- Grep audit of the package: no network-related imports (socket/urllib/
  http/requests) anywhere.
- `python -m compileall pet_log_mcp` → clean.

## Known gaps / future ideas

- Medication "reminders" stay passive by design: the tool lists recorded
  schedules (and would show them in a handoff summary); it does not assess
  adherence or push time-based alerts, so it can never be mistaken for
  dosing advice.
- No scheduled notification resources/prompts (MCP `resources/*`,
  `prompts/*`) — tools only, the surface most clients use today.
- No data migration/schema versioning; the JSON files are simple lists and
  the loader is tolerant, but big structural changes would need a
  migration step later.
- No abbreviations/aliases for unit normalization (e.g., "kg"/"lb" only).
- Multi-pet summaries ("all pets, one summary") could be a future tool.
- Handoff summary picks the latest feeding/visit/weight entry; a wider
  history window option is a possible enhancement.

## Notes for maintainers

- Tests deliberately use a `FakeStore` (in-memory subclass) to mock
  persistence in tool/protocol tests, plus optional real-file tests and a
  subprocess e2e — no test should ever touch the network.
- The end-to-end tests set `PET_LOG_DATA_DIR` to a pytest tmp path, so
  running the suite never writes into a real data folder.
