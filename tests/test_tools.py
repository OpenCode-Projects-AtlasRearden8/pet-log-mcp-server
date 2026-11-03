"""Tool tests with mocked/store-fake persistence (no real files)."""

import pytest

from pet_log_mcp.tools import DISCLAIMER, ToolError, TOOLS

from conftest import FakeStore


def call(store, name, arguments):
    """Simulate an MCP tools/call against a (fake) store."""
    return TOOLS[name]["handler"](store, arguments)


def test_add_pet_and_list_pets(fake_store):
    call(fake_store, "add_pet", {"name": "Mochi", "species": "cat"})
    call(fake_store, "add_pet", {"name": "Biscuit", "species": "dog"})
    out = call(fake_store, "list_pets", {})
    assert "Mochi (cat)" in out
    assert "Biscuit (dog)" in out


def test_add_pet_rejects_duplicates(fake_store):
    call(fake_store, "add_pet", {"name": "Mochi"})
    with pytest.raises(ToolError):
        call(fake_store, "add_pet", {"name": "mochi"})


def test_add_pet_requires_name(fake_store):
    with pytest.raises(ToolError, match="name"):
        call(fake_store, "add_pet", {"species": "cat"})


def test_unknown_pet_is_rejected(fake_store):
    with pytest.raises(ToolError, match="Unknown pet"):
        call(fake_store, "add_weight", {"pet_name": "Ghost", "weight": 4.2})


def test_vet_visit_history_roundtrip(fake_store):
    call(fake_store, "add_pet", {"name": "Mochi"})
    call(fake_store, "add_vet_visit", {"pet_name": "Mochi", "date": "2026-06-01", "reason": "annual checkup"})
    call(fake_store, "add_vet_visit", {"pet_name": "Mochi", "date": "2026-09-15", "reason": "vaccines"})
    out = call(fake_store, "list_vet_visits", {"pet_name": "Mochi"})
    assert "2026-06-01" in out and "annual checkup" in out
    assert "2026-09-15" in out and "vaccines" in out


def test_vet_visit_requires_reason(fake_store):
    call(fake_store, "add_pet", {"name": "Mochi"})
    with pytest.raises(ToolError, match="reason"):
        call(fake_store, "add_vet_visit", {"pet_name": "Mochi"})


def test_bad_date_is_rejected(fake_store):
    call(fake_store, "add_pet", {"name": "Mochi"})
    with pytest.raises(ToolError, match="ISO"):
        call(fake_store, "add_vet_visit", {"pet_name": "Mochi", "reason": "r", "date": "June 5"})


def test_medication_organizer_lists_schedule(fake_store):
    call(fake_store, "add_pet", {"name": "Biscuit"})
    out = call(fake_store, "add_medication", {
        "pet_name": "Biscuit",
        "name": "heartworm tablet",
        "dose": "per vet label",
        "schedule": "1st of the month",
    })
    listed = call(fake_store, "list_medications", {"pet_name": "Biscuit"})
    assert "heartworm tablet" in out
    assert "Biscuit" in listed
    assert "1st of the month" in listed


def test_weight_trend_computes_deltas(fake_store):
    call(fake_store, "add_pet", {"name": "Mochi"})
    call(fake_store, "add_weight", {"pet_name": "Mochi", "date": "2026-01-01", "weight": 4.0})
    call(fake_store, "add_weight", {"pet_name": "Mochi", "date": "2026-02-01", "weight": 4.3})
    out = call(fake_store, "weight_trend", {"pet_name": "Mochi"})
    assert "2026-01-01" in out and "4" in out
    assert "+0.30 kg" in out
    call(fake_store, "add_weight", {"pet_name": "Mochi", "date": "2026-03-01", "weight": 4.1, "unit": "lb"})
    mixed = call(fake_store, "weight_trend", {"pet_name": "Mochi"})
    assert "previous entry used kg" in mixed


def test_weight_rejects_bad_values(fake_store):
    call(fake_store, "add_pet", {"name": "Mochi"})
    with pytest.raises(ToolError):
        call(fake_store, "add_weight", {"pet_name": "Mochi", "weight": -1})
    with pytest.raises(ToolError):
        call(fake_store, "add_weight", {"pet_name": "Mochi", "weight": 4, "unit": "stones"})


def test_feeding_notes_newest_first_and_limit(fake_store):
    call(fake_store, "add_pet", {"name": "Biscuit"})
    for d, note in (("2026-01-01", "ate everything"), ("2026-01-02", "picky")):
        call(fake_store, "add_feeding_note", {"pet_name": "Biscuit", "date": d, "notes": note})
    out = call(fake_store, "list_feeding_notes", {"pet_name": "Biscuit"})
    assert out.index("picky") < out.index("ate everything")
    limited = call(fake_store, "list_feeding_notes", {"pet_name": "Biscuit", "limit": 1})
    assert "ate everything" not in limited


def test_handoff_note_requires_audience_member(fake_store):
    call(fake_store, "add_pet", {"name": "Mochi"})
    with pytest.raises(ToolError, match="audience"):
        call(fake_store, "add_handoff_note", {"pet_name": "Mochi", "audience": "dentist", "notes": "x"})


def test_handoff_summary_pulls_everything_together(fake_store):
    call(fake_store, "add_pet", {"name": "Mochi"})
    call(fake_store, "add_medication", {"pet_name": "Mochi", "name": "fish oil", "schedule": "daily"})
    call(fake_store, "add_feeding_note", {"pet_name": "Mochi", "food": "salmon kibble", "amount": "1/4 cup", "date": "2026-02-01"})
    call(fake_store, "add_vet_visit", {"pet_name": "Mochi", "date": "2026-01-10", "reason": "dental check"})
    call(fake_store, "add_weight", {"pet_name": "Mochi", "date": "2026-02-02", "weight": 4.5})
    call(fake_store, "add_handoff_note", {"pet_name": "Mochi", "audience": "sitter", "notes": "Likes her feather wand."})
    summary = call(fake_store, "get_handoff_summary", {"pet_name": "Mochi", "audience": "sitter"})
    assert "feather wand" in summary
    assert "fish oil" in summary and "daily" in summary
    assert "salmon kibble" in summary
    assert "dental check" in summary
    assert "4.5 kg" in summary
    assert DISCLAIMER in summary


def test_handoff_summary_filters_by_audience(fake_store):
    call(fake_store, "add_pet", {"name": "Mochi"})
    call(fake_store, "add_handoff_note", {"pet_name": "Mochi", "audience": "sitter", "notes": "keep litter box clean"})
    call(fake_store, "add_handoff_note", {"pet_name": "Mochi", "audience": "groomer", "notes": "hates the dryer"})
    out = call(fake_store, "get_handoff_summary", {"pet_name": "Mochi", "audience": "groomer"})
    assert "hates the dryer" in out
    assert "litter box" not in out


def test_delete_record_roundtrip(fake_store):
    call(fake_store, "add_pet", {"name": "Mochi"})
    call(fake_store, "add_vet_visit", {"pet_name": "Mochi", "reason": "checkup"})
    rid = fake_store.read("vet_visits")[0]["id"]
    out = call(fake_store, "delete_record", {"collection": "vet_visits", "id": rid})
    assert rid in out
    assert fake_store.read("vet_visits") == []


def test_all_tool_specs_have_handlers_and_schemas():
    for name, spec in TOOLS.items():
        assert callable(spec["handler"]), name
        assert spec["inputSchema"]["type"] == "object", name
        assert isinstance(spec["inputSchema"]["required"], list), name
        assert spec["description"].strip(), name
