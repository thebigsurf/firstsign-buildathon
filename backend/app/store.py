"""Reference data loading and the storage interface.

`Reference` loads the read-only seed data from data/ once.
`Store` is the mutable state (orders, audit, ASHA reports, explanations, approvals,
parse log). All high-level behaviour lives in `Store`; subclasses only provide four
primitives, so `LocalStore` (in-memory + JSON file) and `FirestoreStore` behave the same.
"""

from __future__ import annotations

import copy
import csv
import json
import logging
import threading
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from .config import Settings
from .errors import AppError

log = logging.getLogger("firstsign.store")

COLLECTIONS = ("orders", "parses", "audit", "asha_reports", "explanations", "approvals", "parse_log")


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


# ---------------------------------------------------------------- reference data


def _read_csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    if not path.exists():
        raise AppError(500, "data_missing", f"Seed data file is missing: {path.name}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise AppError(500, "data_invalid", f"{path.name} is missing columns: {sorted(missing)}")
        return [{k: (v or "").strip() for k, v in row.items()} for row in reader]


def _read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise AppError(500, "data_missing", f"Seed data file is missing: {path.name}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _num(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass
class Reference:
    """Seed data from data/ (simulated for the demo)."""

    catalogue: list[dict[str, str]]
    groups: list[dict[str, Any]]
    pincodes: list[dict[str, Any]]
    chemists: list[dict[str, Any]]
    distributor: dict[str, Any]
    history: pd.DataFrame
    asha: list[dict[str, Any]]
    localities: list[dict[str, Any]]
    inbox: list[dict[str, Any]]
    data_dir: Path
    _chemist_by_id: dict[str, dict[str, Any]] = field(default_factory=dict, repr=False)
    _pin_by_code: dict[str, dict[str, Any]] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self._chemist_by_id = {c["chemist_id"]: c for c in self.chemists}
        self._pin_by_code = {p["pin"]: p for p in self.pincodes}

    @classmethod
    def load(cls, data_dir: Path) -> "Reference":
        catalogue = _read_csv(
            data_dir / "catalogue.csv",
            {"sku_id", "brand", "strength", "form", "pack", "molecule", "group", "unit", "aliases"},
        )
        pincodes = [
            {**r, "lat": _num(r["lat"]), "lng": _num(r["lng"]), "population": int(_num(r["population"]))}
            for r in _read_csv(data_dir / "pincodes.csv", {"pin", "area", "ward", "lat", "lng", "population"})
        ]
        chemists = [
            {**r, "lat": _num(r["lat"]), "lng": _num(r["lng"])}
            for r in _read_csv(
                data_dir / "chemists.csv",
                {"chemist_id", "shop_name", "owner_first_name", "pin", "lat", "lng", "language", "software"},
            )
        ]
        localities = [
            {**r, "lat": _num(r["lat"]), "lng": _num(r["lng"]), "households": int(_num(r["households"]))}
            for r in _read_csv(
                data_dir / "localities.csv", {"pin", "locality_id", "name", "landmark", "lat", "lng", "households"}
            )
        ]
        asha = _read_csv(data_dir / "asha.csv", {"asha_id", "first_name", "pin", "language"})
        history_rows = _read_csv(data_dir / "history.csv", {"date", "pin", "group", "units", "chemists_ordering"})
        history = pd.DataFrame(history_rows)
        if history.empty:
            raise AppError(500, "data_invalid", "history.csv has no rows.")
        history["date"] = pd.to_datetime(history["date"])
        history["units"] = pd.to_numeric(history["units"], errors="coerce").fillna(0.0)
        history["chemists_ordering"] = pd.to_numeric(history["chemists_ordering"], errors="coerce").fillna(0.0)
        return cls(
            catalogue=catalogue,
            groups=_read_json(data_dir / "groups.json"),
            pincodes=pincodes,
            chemists=chemists,
            distributor=_read_json(data_dir / "distributor.json"),
            history=history,
            asha=asha,
            localities=localities,
            inbox=_read_json(data_dir / "demo_inbox.json", default=[]),
            data_dir=data_dir,
        )

    def chemist(self, chemist_id: str) -> dict[str, Any] | None:
        return self._chemist_by_id.get(chemist_id)

    def pin(self, code: str) -> dict[str, Any] | None:
        return self._pin_by_code.get(code)

    def area(self, code: str) -> str:
        entry = self._pin_by_code.get(code)
        return entry["area"] if entry else code

    def group_label(self, group_id: str) -> str:
        for group in self.groups:
            if group["id"] == group_id:
                return str(group.get("label", group_id))
        return group_id

    def is_chronic(self, group_id: str) -> bool:
        for group in self.groups:
            if group["id"] == group_id:
                return bool(group.get("is_chronic", False))
        return False

    def asha_by_id(self, asha_id: str) -> dict[str, Any] | None:
        return next((a for a in self.asha if a["asha_id"] == asha_id), None)

    def locality(self, locality_id: str) -> dict[str, Any] | None:
        return next((x for x in self.localities if x["locality_id"] == locality_id), None)

    def inbox_item(self, message_id: str) -> dict[str, Any] | None:
        return next((m for m in self.inbox if m.get("id") == message_id), None)

    def resolve_data_path(self, relative: str) -> Path | None:
        """Resolve a path from demo_inbox.json under data/ or data/samples, refusing escapes."""
        root = self.data_dir.resolve()
        for base in (root, root / "samples"):
            candidate = (base / relative).resolve()
            if candidate.is_file() and root in candidate.parents:
                return candidate
        return None


# ------------------------------------------------------------------------- store


class Store(ABC):
    """Mutable demo state. Subclasses implement the four primitives only."""

    # primitives ------------------------------------------------------------
    @abstractmethod
    def _append(self, collection: str, doc: dict[str, Any]) -> None: ...

    @abstractmethod
    def _list(self, collection: str) -> list[dict[str, Any]]: ...

    @abstractmethod
    def _get(self, collection: str, key: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def _put(self, collection: str, key: str, doc: dict[str, Any]) -> None: ...

    # version counter used to invalidate computed signal -----------------------
    def __init__(self) -> None:
        self._version = 0

    @property
    def version(self) -> int:
        return self._version

    def _bump(self) -> None:
        self._version += 1

    # orders ----------------------------------------------------------------
    def add_order(self, order: dict[str, Any]) -> None:
        self._append("orders", order)
        self._bump()

    def list_orders(self) -> list[dict[str, Any]]:
        return self._list("orders")

    # parses (the latest parse per message, used to diff clerk edits) ----------
    def save_parse(self, key: str, parsed: dict[str, Any]) -> None:
        self._put("parses", key, parsed)

    def get_parse(self, key: str) -> dict[str, Any] | None:
        return self._get("parses", key)

    def log_parse(self, entry: dict[str, Any]) -> None:
        self._append("parse_log", entry)

    def parse_log(self) -> list[dict[str, Any]]:
        return self._list("parse_log")

    # audit -----------------------------------------------------------------
    def add_audit(self, actor: str, kind: str, ref_id: str, summary: str, *, before: dict[str, Any] | None = None,
                  after: dict[str, Any] | None = None, detail: dict[str, Any] | None = None) -> dict[str, Any]:
        entry = {"id": new_id("aud"), "ts": utc_now(), "actor": actor, "approved_by": actor, "kind": kind,
                 "ref_id": ref_id, "summary": summary, "before": before, "after": after, "detail": detail or {}}
        self._append("audit", entry)
        return entry

    def list_audit(self) -> list[dict[str, Any]]:
        return self._list("audit")

    # ASHA reports ----------------------------------------------------------
    def add_asha_report(self, report: dict[str, Any]) -> None:
        self._append("asha_reports", report)
        self._bump()

    def list_asha_reports(self) -> list[dict[str, Any]]:
        return self._list("asha_reports")

    # agent explanations and approved actions ------------------------------------
    def save_explanation(self, alert_id: str, doc: dict[str, Any]) -> None:
        self._put("explanations", alert_id, doc)

    def get_explanation(self, alert_id: str) -> dict[str, Any] | None:
        return self._get("explanations", alert_id)

    def add_approval(self, approval: dict[str, Any]) -> None:
        self._append("approvals", approval)

    def list_approvals(self) -> list[dict[str, Any]]:
        return self._list("approvals")


class LocalStore(Store):
    """Thread-safe in-memory store persisted to a JSON file so a restart keeps demo state."""

    def __init__(self, state_file: Path | None = None) -> None:
        super().__init__()
        self._lock = threading.RLock()
        self._file = state_file
        self._lists: dict[str, list[dict[str, Any]]] = {c: [] for c in COLLECTIONS}
        self._maps: dict[str, dict[str, dict[str, Any]]] = {c: {} for c in COLLECTIONS}
        self._load()

    def _load(self) -> None:
        if not self._file or not self._file.exists():
            return
        try:
            raw = json.loads(self._file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            log.warning("state file unreadable; starting with empty state")
            return
        for name in COLLECTIONS:
            entry = raw.get(name, {})
            self._lists[name] = list(entry.get("list", []))
            self._maps[name] = dict(entry.get("map", {}))
        self._version = 1

    def _persist(self) -> None:
        if not self._file:
            return
        payload = {n: {"list": self._lists[n], "map": self._maps[n]} for n in COLLECTIONS}
        try:
            self._file.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._file.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self._file)
        except OSError:
            log.warning("could not persist state file")

    def _append(self, collection: str, doc: dict[str, Any]) -> None:
        with self._lock:
            self._lists[collection].append(copy.deepcopy(doc))
            self._persist()

    def _list(self, collection: str) -> list[dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(self._lists[collection])

    def _get(self, collection: str, key: str) -> dict[str, Any] | None:
        with self._lock:
            doc = self._maps[collection].get(key)
            return copy.deepcopy(doc) if doc is not None else None

    def _put(self, collection: str, key: str, doc: dict[str, Any]) -> None:
        with self._lock:
            self._maps[collection][key] = copy.deepcopy(doc)
            self._persist()

    def reset(self) -> None:
        """Clear all demo state (used by tests and the reset endpoint)."""
        with self._lock:
            self._lists = {c: [] for c in COLLECTIONS}
            self._maps = {c: {} for c in COLLECTIONS}
            self._persist()
            self._bump()


class FirestoreStore(Store):
    """Same interface on Cloud Firestore. google-cloud-firestore is imported lazily.

    Appended documents carry a monotonically increasing `_seq` so listing keeps order.
    """

    def __init__(self, project: str) -> None:
        super().__init__()
        from google.cloud import firestore  # lazy: optional dependency

        self._db = firestore.Client(project=project)
        self._firestore = firestore
        self._lock = threading.Lock()

    def _append(self, collection: str, doc: dict[str, Any]) -> None:
        with self._lock:
            payload = {**doc, "_seq": self._firestore.SERVER_TIMESTAMP}
            self._db.collection(collection).document(new_id("d")).set(payload)

    def _list(self, collection: str) -> list[dict[str, Any]]:
        docs = self._db.collection(collection).order_by("_seq").stream()
        return [{k: v for k, v in d.to_dict().items() if k != "_seq"} for d in docs]

    def _get(self, collection: str, key: str) -> dict[str, Any] | None:
        snap = self._db.collection(f"{collection}_kv").document(key).get()
        return snap.to_dict()["doc"] if snap.exists else None

    def _put(self, collection: str, key: str, doc: dict[str, Any]) -> None:
        self._db.collection(f"{collection}_kv").document(key).set({"doc": doc})


def build_store(settings: Settings) -> Store:
    """Pick the store from STORAGE; fall back to local with a warning if Firestore is unusable."""
    if settings.storage == "firestore":
        try:
            return FirestoreStore(settings.google_cloud_project)
        except Exception as exc:  # missing package or credentials
            log.warning("Firestore unavailable (%s); using local storage", type(exc).__name__)
    return LocalStore(settings.state_file)
