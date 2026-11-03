"""Shared pytest fixtures: temp data dir and a fresh store per test."""

import json
from pathlib import Path

import pytest

from pet_log_mcp.store import JsonStore


@pytest.fixture()
def data_dir(tmp_path: Path) -> Path:
    return tmp_path / "pet-data"


@pytest.fixture()
def store(data_dir: Path) -> JsonStore:
    return JsonStore(data_dir)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


# Simulated in-memory store factory used to "mock" persistence in some tests.


class FakeStore(JsonStore):
    """JsonStore subclass that keeps data in RAM only (no file writes)."""

    def __init__(self):
        super().__init__(":memory-unused:")
        self._memory: dict[str, list] = {}

    def read(self, collection: str) -> list[dict]:
        return list(self._memory.get(collection, []))

    def write(self, collection: str, records: list[dict]) -> None:
        self._memory[collection] = list(records)


@pytest.fixture()
def fake_store() -> FakeStore:
    return FakeStore()
