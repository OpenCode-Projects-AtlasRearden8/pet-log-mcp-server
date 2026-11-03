"""Tool implementations for the pet-log MCP server.

Every tool is an organizing/summarizing helper for the owner's own notes.
Nothing here dispenses veterinary, medical, or feeding advice; all output is
derived from the user's own recorded notes plus disarmingly short education
disclaimers.
"""

from datetime import date

from .store import COLLECTIONS, JsonStore

DISCLAIMER = (
    "Education and organizing only - this is not veterinary advice. "
    "Consult your veterinarian for medical decisions."
)


class ToolError(Exception):
    """Raised for user-facing tool failures (bad input, missing records)."""


def _validate_date(value: str, field: str = "date") -> str:
    if not isinstance(value, str):
        raise ToolError(f"{field} must be a string in YYYY-MM-DD format.")
    try:
        date.fromisoformat(value)
    except ValueError:
        raise ToolError(
            f"{field} {value!r} is not a valid ISO date (YYYY-MM-DD)."
        ) from None
    return value


def _clean(value, field: str, required: bool = False) -> str:
    if value is None:
        if required:
            raise ToolError(f"{field} is required.")
        return ""
    if not isinstance(value, str):
        raise ToolError(f"{field} must be a string.")
    text = value.strip()
    if required and not text:
        raise ToolError(f"{field} must not be empty.")
    return text


def _require(store: JsonStore, args: dict, pet_name) -> str:
    pet = _clean(pet_name or args.get("pet_name"), "pet_name", required=True)
    try:
        store.require_pet(pet)
    except LookupError as exc:
        raise ToolError(str(exc)) from None
    return pet


def _today() -> str:
    return date.today().isoformat()


# -- pet tools -------------------------------------------------------------


def add_pet(store: JsonStore, args: dict) -> str:
    name = _clean(args.get("name"), "name", required=True)
    if name.lower() in {p.lower() for p in store.pet_names()}:
        raise ToolError(f"A pet named {name!r} already exists.")
    store.append(
        "pets",
        {
            "name": name,
            "species": _clean(args.get("species"), "species"),
            "birth_date": _clean(args.get("birth_date"), "birth_date"),
            "notes": _clean(args.get("notes"), "notes"),
        },
    )
    return f"Added pet {name!r} to the log. {DISCLAIMER}"


def list_pets(store: JsonStore, args: dict) -> str:
    pets = store.read("pets")
    if not pets:
        return "No pets in the log yet. Use add_pet to add one."
    lines = [
        f"- {p['name']}"
        + (f" ({p['species']})" if p.get("species") else "")
        + (f" - {p['notes']}" if p.get("notes") else "")
        for p in pets
    ]
    return "Pets in the log:\n" + "\n".join(lines)


# -- vet visits ------------------------------------------------------------


def add_vet_visit(store: JsonStore, args: dict) -> str:
    pet = _require(store, args, args.get("pet_name"))
    visit = {
        "pet_name": pet,
        "date": _validate_date(args.get("date") or _today()),
        "clinic": _clean(args.get("clinic"), "clinic"),
        "reason": _clean(args.get("reason"), "reason", required=True),
        "outcome": _clean(args.get("outcome"), "outcome"),
        "notes": _clean(args.get("notes"), "notes"),
    }
    record = store.append("vet_visits", visit)
    return (
        f"Logged {pet!r} vet visit on {visit['date']}"
        f" (id {record['id']}). {DISCLAIMER}"
    )


def list_vet_visits(store: JsonStore, args: dict) -> str:
    pet = _clean(args.get("pet_name"), "pet_name")
    visits = store.read("vet_visits")
    if pet:
        try:
            store.require_pet(pet)
        except LookupError as exc:
            raise ToolError(str(exc)) from None
        visits = [v for v in visits if v.get("pet_name", "").lower() == pet.lower()]
    if not visits:
        return "No vet visits recorded."
    visits.sort(key=lambda v: v.get("date", ""))
    lines = [
        f"- {v.get('date', '?')} {v.get('pet_name', '?')}: {v.get('reason', '')}"
        + (f" @ {v['clinic']}" if v.get("clinic") else "")
        + (f" - {v['outcome']}" if v.get("outcome") else "")
        + (f" (notes: {v['notes']})" if v.get("notes") else "")
        for v in visits
    ]
    return "Vet-visit history:\n" + "\n".join(lines)


# -- medications -----------------------------------------------------------


def add_medication(store: JsonStore, args: dict) -> str:
    pet = _require(store, args, args.get("pet_name"))
    name = _clean(args.get("name"), "name", required=True)
    record = store.append(
        "medications",
        {
            "pet_name": pet,
            "name": name,
            "dose": _clean(args.get("dose"), "dose"),
            "schedule": _clean(args.get("schedule"), "schedule"),
            "start_date": args.get("start_date") or _today(),
            "notes": _clean(args.get("notes"), "notes"),
        },
    )
    return (
        f"Added medication {name!r} for {pet!r} (id {record['id']}). "
        "Keep following your veterinarian's instructions; this log does not "
        "issue dosing advice."
    )


def list_medications(store: JsonStore, args: dict) -> str:
    pet = _clean(args.get("pet_name"), "pet_name")
    meds = store.read("medications")
    if pet:
        try:
            store.require_pet(pet)
        except LookupError as exc:
            raise ToolError(str(exc)) from None
        meds = [m for m in meds if m.get("pet_name", "").lower() == pet.lower()]
    if not meds:
        return "No medications on the schedule."
    meds.sort(key=lambda m: m.get("pet_name", ""))
    lines = [
        f"- {m.get('pet_name', '?')}: {m.get('name', '?')}"
        + (f" | dose: {m['dose']}" if m.get("dose") else "")
        + (f" | schedule: {m['schedule']}" if m.get("schedule") else "")
        + (f" | since {m['start_date']}" if m.get("start_date") else "")
        + (f" | notes: {m['notes']}" if m.get("notes") else "")
        for m in meds
    ]
    return "Medication organizer (your own recorded schedule, not advice)\n" + "\n".join(lines)


# -- weights ---------------------------------------------------------------


def _parse_weight(args: dict):
    raw = args.get("weight")
    if not isinstance(raw, (int, float)) or isinstance(raw, bool):
        raise ToolError("weight must be a number.")
    weight = float(raw)
    if weight <= 0 or weight > 1000:
        raise ToolError("weight must be a positive number in a sane range.")
    unit = _clean(args.get("unit", "kg"), "unit").lower() or "kg"
    if unit not in ("kg", "lb"):
        raise ToolError("unit must be 'kg' or 'lb'.")
    return weight, unit


def add_weight(store: JsonStore, args: dict) -> str:
    pet = _require(store, args, args.get("pet_name"))
    weight, unit = _parse_weight(args)
    record = store.append(
        "weights",
        {
            "pet_name": pet,
            "date": _validate_date(args.get("date") or _today()),
            "weight": weight,
            "unit": unit,
        },
    )
    return f"Logged {pet!r} at {weight:g} {unit} on {record['date']}."


def weight_trend(store: JsonStore, args: dict) -> str:
    pet = _clean(args.get("pet_name"), "pet_name")
    weights = store.read("weights")
    if pet:
        try:
            store.require_pet(pet)
        except LookupError as exc:
            raise ToolError(str(exc)) from None
        weights = [w for w in weights if w.get("pet_name", "").lower() == pet.lower()]
    if not weights:
        return "No weight entries recorded yet."
    weights.sort(key=lambda w: (w.get("pet_name", ""), w.get("date", "")))
    lines = ["Weight trend (from your own notes, not a health assessment):"]
    prev: dict[str, dict] = {}
    for w in weights:
        pet_name = w.get("pet_name", "?")
        unit = w.get("unit", "kg")
        weight = w.get("weight", 0)
        note = f"- [{pet_name}] {w.get('date', '?')}: {weight:g} {unit}"
        prior = prev.get(pet_name)
        if prior:
            delta = weight - prior["weight"]
            if prior["unit"] == unit:
                note += f" (change {delta:+.2f} {unit} since {prior['date']})"
            else:
                note += f" (previous entry used {prior['unit']})"
        prev[pet_name] = {"weight": weight, "unit": unit, "date": w.get("date", "")}
        lines.append(note)
    return "\n".join(lines)


# -- feeding notes ---------------------------------------------------------


def add_feeding_note(store: JsonStore, args: dict) -> str:
    pet = _require(store, args, args.get("pet_name"))
    record = store.append(
        "feeding_notes",
        {
            "pet_name": pet,
            "date": _validate_date(args.get("date") or _today()),
            "food": _clean(args.get("food"), "food"),
            "amount": _clean(args.get("amount"), "amount"),
            "appetite": _clean(args.get("appetite"), "appetite"),
            "notes": _clean(args.get("notes"), "notes"),
        },
    )
    return f"Logged feeding note for {pet!r} (id {record['id']})."


def list_feeding_notes(store: JsonStore, args: dict) -> str:
    pet = _clean(args.get("pet_name"), "pet_name")
    limit = args.get("limit", 20)
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ToolError("limit must be a positive integer.")
    notes = store.read("feeding_notes")
    if pet:
        try:
            store.require_pet(pet)
        except LookupError as exc:
            raise ToolError(str(exc)) from None
        notes = [n for n in notes if n.get("pet_name", "").lower() == pet.lower()]
    notes.sort(key=lambda n: n.get("date", ""), reverse=True)
    if not notes:
        return "No feeding notes recorded yet."
    lines = [
        f"- {n.get('date', '?')} [{n.get('pet_name', '?')}]"
        + (f" {n['food']}" if n.get("food") else "")
        + (f" ({n['amount']})" if n.get("amount") else "")
        + (f" appetite: {n['appetite']}" if n.get("appetite") else "")
        + (f" - {n['notes']}" if n.get("notes") else "")
        for n in notes[:limit]
    ]
    return f"Feeding notes (newest first, showing {min(limit, len(notes))}):\n" + "\n".join(lines)


# -- handoff notes ---------------------------------------------------------

AUDIENCES = ("groomer", "sitter", "vet-tech", "family")


def add_handoff_note(store: JsonStore, args: dict) -> str:
    pet = _require(store, args, args.get("pet_name"))
    audience = _clean(args.get("audience"), "audience", required=True).lower()
    if audience not in AUDIENCES:
        raise ToolError(f"audience must be one of: {', '.join(AUDIENCES)}.")
    notes = _clean(args.get("notes"), "notes", required=True)
    record = store.append(
        "handoff_notes",
        {
            "pet_name": pet,
            "date": _validate_date(args.get("date") or _today()),
            "audience": audience,
            "notes": notes,
        },
    )
    return f"Added {audience} handoff note for {pet!r} (id {record['id']})."


def get_handoff_summary(store: JsonStore, args: dict) -> str:
    pet = _clean(args.get("pet_name"), "pet_name", required=True)
    try:
        store.require_pet(pet)
    except LookupError as exc:
        raise ToolError(str(exc)) from None
    audience = _clean(args.get("audience"), "audience").lower()
    if audience and audience not in AUDIENCES:
        raise ToolError(f"audience must be one of: {', '.join(AUDIENCES)}.")

    lower = pet.lower()
    handoffs = [
        h for h in store.read("handoff_notes")
        if h.get("pet_name", "").lower() == lower
        and (not audience or h.get("audience") == audience)
    ]
    handoffs.sort(key=lambda h: h.get("date", ""), reverse=True)
    meds = [m for m in store.read("medications") if m.get("pet_name", "").lower() == lower]
    feedings = [f for f in store.read("feeding_notes") if f.get("pet_name", "").lower() == lower]
    feedings.sort(key=lambda f: f.get("date", ""), reverse=True)
    visits = [v for v in store.read("vet_visits") if v.get("pet_name", "").lower() == lower]
    visits.sort(key=lambda v: v.get("date", ""), reverse=True)
    weights = [w for w in store.read("weights") if w.get("pet_name", "").lower() == lower]
    weights.sort(key=lambda w: w.get("date", ""), reverse=True)

    lines = [f"Handoff summary for {pet} (your own notes, organized):"]
    if handoffs:
        lines.append("Your speaker notes:")
        lines += [f"- [{h.get('date', '?')}/{h.get('audience', '?')}] {h.get('notes', '')}" for h in handoffs]
    if meds:
        lines.append("Medications on your schedule:")
        lines += [
            f"- {m.get('name', '?')}"
            + (f" ({m['dose']})" if m.get("dose") else "")
            + (f" - {m['schedule']}" if m.get("schedule") else "")
            for m in meds
        ]
    if feedings:
        latest = feedings[0]
        lines.append(
            f"Most recent feeding note: {latest.get('date', '?')} "
            + (latest.get("food") or "no food recorded")
            + (f" ({latest['amount']})" if latest.get("amount") else "")
        )
    if visits:
        latest_visit = visits[0]
        lines.append(
            f"Most recent vet visit: {latest_visit.get('date', '?')} "
            f"- {latest_visit.get('reason', 'no reason recorded')}"
        )
    if weights:
        latest_w = weights[0]
        lines.append(
            f"Latest recorded weight: {latest_w.get('weight', '?'):g} "
            f"{latest_w.get('unit', 'kg')} on {latest_w.get('date', '?')}"
        )
    if len(lines) == 1:
        lines.append("(No notes recorded for this pet yet.)")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def delete_record(store: JsonStore, args: dict) -> str:
    collection = _clean(args.get("collection"), "collection", required=True)
    record_id = _clean(args.get("id"), "id", required=True)
    try:
        deleted = store.remove(collection, record_id)
    except ValueError as exc:
        raise ToolError(str(exc)) from None
    except LookupError as exc:
        raise ToolError(str(exc)) from None
    name = deleted.get("name") or deleted.get("reason") or record_id
    return f"Deleted '{collection}' record {name!r} (id {record_id})."


# -- MCP tool registry -------------------------------------------------

def _schema(properties: dict, required: list[str]) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


_pet = {"type": "string", "description": "Pet's name as recorded in the log."}
_date = {"type": "string", "description": "ISO date (YYYY-MM-DD); defaults to today when omitted."}
_text = {"type": "string"}

TOOLS: dict[str, dict] = {
    "add_pet": {
        "title": "Add pet",
        "description": "Add a pet to the log so its notes can be tracked.",
        "inputSchema": _schema(
            {
                "name": {"type": "string"},
                "species": _text,
                "birth_date": {"type": "string", "description": "ISO date (YYYY-MM-DD)."},
                "notes": _text,
            },
            ["name"],
        ),
        "handler": add_pet,
    },
    "list_pets": {
        "title": "List pets",
        "description": "List every pet recorded in the log.",
        "inputSchema": _schema({}, []),
        "handler": list_pets,
    },
    "add_vet_visit": {
        "title": "Log vet visit",
        "description": "Record a vet visit in the history for one pet.",
        "inputSchema": _schema(
            {
                "pet_name": _pet,
                "date": _date,
                "clinic": _text,
                "reason": {"type": "string", "description": "Why the visit happened."},
                "outcome": _text,
                "notes": _text,
            },
            ["pet_name", "reason"],
        ),
        "handler": add_vet_visit,
    },
    "list_vet_visits": {
        "title": "List vet visits",
        "description": "List vet-visit history, or only one pet's visits.",
        "inputSchema": _schema({"pet_name": _pet}, []),
        "handler": list_vet_visits,
    },
    "add_medication": {
        "title": "Add medication to schedule",
        "description": (
            "Record a medication the veterinarian prescribed and the schedule "
            "you were told to follow. Organizing only; never dosing advice."
        ),
        "inputSchema": _schema(
            {
                "pet_name": _pet,
                "name": {"type": "string", "description": "Medication name."},
                "dose": _text,
                "schedule": {"type": "string", "description": "e.g. 'ampm 2x daily'."},
                "start_date": {"type": "string", "description": "ISO date (YYYY-MM-DD)."},
                "notes": _text,
            },
            ["pet_name", "name"],
        ),
        "handler": add_medication,
    },
    "list_medications": {
        "title": "List medication schedule",
        "description": "List recorded medications and schedules, or only one pet's.",
        "inputSchema": _schema({"pet_name": _pet}, []),
        "handler": list_medications,
    },
    "add_weight": {
        "title": "Log weight entry",
        "description": "Record one weight measurement (from your own scale or vet report).",
        "inputSchema": _schema(
            {
                "pet_name": _pet,
                "weight": {"type": "number", "description": "Numeric weight value."},
                "unit": {"type": "string", "description": "'kg' (default) or 'lb'."},
                "date": _date,
            },
            ["pet_name", "weight"],
        ),
        "handler": add_weight,
    },
    "weight_trend": {
        "title": "Weight trend",
        "description": "Show recorded weights in date order with change between entries.",
        "inputSchema": _schema({"pet_name": _pet}, []),
        "handler": weight_trend,
    },
    "add_feeding_note": {
        "title": "Log feeding note",
        "description": "Record a feeding observation (what was offered, appetite, notes).",
        "inputSchema": _schema(
            {
                "pet_name": _pet,
                "date": _date,
                "food": _text,
                "amount": _text,
                "appetite": _text,
                "notes": _text,
            },
            ["pet_name"],
        ),
        "handler": add_feeding_note,
    },
    "list_feeding_notes": {
        "title": "List feeding notes",
        "description": "List recent feeding notes, newest first.",
        "inputSchema": _schema(
            {"pet_name": _pet, "limit": {"type": "integer", "description": "Max notes (default 20)."}},
            [],
        ),
        "handler": list_feeding_notes,
    },
    "add_handoff_note": {
        "title": "Add handoff note",
        "description": "Add a note meant for a groomer, sitter, or other caretaker.",
        "inputSchema": _schema(
            {
                "pet_name": _pet,
                "audience": {"type": "string", "description": f"One of: {', '.join(AUDIENCES)}."},
                "notes": {"type": "string", "description": "What the caretaker should know."},
                "date": _date,
            },
            ["pet_name", "audience", "notes"],
        ),
        "handler": add_handoff_note,
    },
    "get_handoff_summary": {
        "title": "Get handoff summary",
        "description": (
            "On-demand summary pulling together handoff notes, medications, the "
            "latest feeding, vet visit, and weight for one pet."
        ),
        "inputSchema": _schema({"pet_name": _pet, "audience": _text}, ["pet_name"]),
        "handler": get_handoff_summary,
    },
    "delete_record": {
        "title": "Delete record",
        "description": "Remove one wrong or duplicated record by id.",
        "inputSchema": _schema(
            {
                "collection": {"type": "string", "description": f"One of: {', '.join(COLLECTIONS)}."},
                "id": {"type": "string", "description": "Record id from a previous add/list result."},
            },
            ["collection", "id"],
        ),
        "handler": delete_record,
    },
}
