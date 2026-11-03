"""Tests for the JSON-folder store: local files only, atomic writes."""

import json

import pytest

from pet_log_mcp.store import COLLECTIONS, JsonStore

from conftest import read_json


def test_reads_empty_collection_from_missing_dir(store):
    assert store.read("pets") == []


def test_unknown_collection_is_rejected(store):
    with pytest.raises(ValueError):
        store.read("not_a_collection")


def test_append_creates_json_file_with_ids_and_timestamps(store):
    record = store.append("pets", {"name": "Mochi"})
    path = store.data_dir / "pets.json"
    assert path.exists()
    on_disk = read_json(path)
    assert on_disk == [
        {
            "name": "Mochi",
            "id": record["id"],
            "created_at": record["created_at"],
        }
    ]
    assert record["id"]
    assert record["created_at"]


def test_append_preserves_existing_records(store):
    store.append("vet_visits", {"pet_name": "Mochi", "reason": "checkup"})
    store.append("vet_visits", {"pet_name": "Mochi", "reason": "vaccine"})
    visits = store.read("vet_visits")
    assert [v["reason"] for v in visits] == ["checkup", "vaccine"]


def test_write_is_atomic_no_tmp_files_left(store, data_dir):
    store.write("pets", [{"name": "A"}])
    leftovers = [p for p in data_dir.iterdir() if p.name != "pets.json"]
    assert leftovers == []


def test_corrupt_file_raises_clear_error(store):
    store.data_dir.mkdir(parents=True)
    (store.data_dir / "pets.json").write_text("{oops", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        store.read("pets")


def test_remove_deletes_matching_record(store):
    first = store.append("medications", {"name": "medicine-a"})
    second = store.append("medications", {"name": "medicine-b"})
    deleted = store.remove("medications", first["id"])
    assert deleted["name"] == "medicine-a"
    ids = [m["id"] for m in store.read("medications")]
    assert ids == [second["id"]]


def test_remove_unknown_id_raises_lookup(store):
    with pytest.raises(LookupError):
        store.remove("pets", "nope")


def test_pet_lookups_case_insensitive(store):
    store.append("pets", {"name": "Mochi"})
    assert store.require_pet("mochi")["name"] == "Mochi"
    with pytest.raises(LookupError):
        store.require_pet("Nobody")


def test_env_var_configures_data_dir(monkeypatch, tmp_path):
    custom = tmp_path / "elsewhere"
    monkeypatch.setenv("PET_LOG_DATA_DIR", str(custom))
    resolved = JsonStore().data_dir == custom
    assert resolved


def test_all_collections_covered():
    assert COLLECTIONS == (
        "pets",
        "vet_visits",
        "medications",
        "weights",
        "feeding_notes",
        "handoff_notes",
    )
