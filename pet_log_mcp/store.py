"""JSON-file store for pet log records.

All data lives in one local folder as plain JSON files. There are no network
calls anywhere in this module: reading and writing is limited to the
filesystem. Writes are atomic (temp file + os.replace) so a crash mid-save
cannot leave a half-written file behind.
"""

import json
import os
import tempfile
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

COLLECTIONS = (
    "pets",
    "vet_visits",
    "medications",
    "weights",
    "feeding_notes",
    "handoff_notes",
)

DEFAULT_DATA_DIR = Path("pet-log-data")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class JsonStore:
    """Simple per-collection JSON list storage in a single folder."""

    def __init__(self, data_dir: Path | str | None = None):
        env_dir = os.environ.get("PET_LOG_DATA_DIR", "")
        self.data_dir = Path(data_dir or env_dir or DEFAULT_DATA_DIR)

    # -- file helpers ------------------------------------------------------

    def _path(self, collection: str) -> Path:
        if collection not in COLLECTIONS:
            raise ValueError(f"Unknown collection: {collection!r}")
        return self.data_dir / f"{collection}.json"

    def read(self, collection: str) -> list[dict]:
        path = self._path(collection)
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, list):
            raise ValueError(
                f"Data file {path} is corrupt: expected a JSON list."
            )
        return data

    def write(self, collection: str, records: list[dict]) -> None:
        path = self._path(collection)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(
            dir=self.data_dir, prefix=f".{path.name}.", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(records, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
            os.replace(tmp, path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    # -- record helpers ----------------------------------------------------

    def append(self, collection: str, record: dict) -> dict:
        records = self.read(collection)
        stored = dict(record)
        stored.setdefault("id", uuid.uuid4().hex[:10])
        stored.setdefault("created_at", _now_iso())
        records.append(stored)
        self.write(collection, records)
        return stored

    def remove(self, collection: str, record_id: str) -> dict:
        records = self.read(collection)
        for i, rec in enumerate(records):
            if rec.get("id") == record_id:
                deleted = records.pop(i)
                self.write(collection, records)
                return deleted
        raise LookupError(
            f"No record with id {record_id!r} in '{collection}'."
        )

    # -- domain lookups ----------------------------------------------------

    def pet_names(self) -> list[str]:
        return sorted(
            pet.get("name", "")
            for pet in self.read("pets")
            if pet.get("name")
        )

    def require_pet(self, name: str) -> dict:
        for pet in self.read("pets"):
            if pet.get("name", "").lower() == name.lower():
                return pet
        raise LookupError(f"Unknown pet {name!r}. Add it first with add_pet.")

    def summary_today(self) -> str:
        return date.today().isoformat()
