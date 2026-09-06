"""Load fixture JSON files from a data directory into model objects."""

import json
from datetime import datetime
from pathlib import Path
from typing import List

from .models import App, RefundEvent, Transaction, UsageEvent


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _read_json(path: Path) -> list:
    with path.open() as f:
        return json.load(f)


def load_apps(data_dir: Path) -> List[App]:
    return [App(**row) for row in _read_json(data_dir / "apps.json")]


def load_transactions(data_dir: Path) -> List[Transaction]:
    rows = _read_json(data_dir / "transactions.json")
    out = []
    for row in rows:
        row = dict(row)
        row["purchase_date"] = _parse_dt(row["purchase_date"])
        out.append(Transaction(**row))
    return out


def load_refund_events(data_dir: Path) -> List[RefundEvent]:
    rows = _read_json(data_dir / "refund_events.json")
    out = []
    for row in rows:
        row = dict(row)
        row["refund_date"] = _parse_dt(row["refund_date"])
        out.append(RefundEvent(**row))
    return out


def load_usage_events(data_dir: Path) -> List[UsageEvent]:
    rows = _read_json(data_dir / "usage_events.json")
    out = []
    for row in rows:
        row = dict(row)
        row["timestamp"] = _parse_dt(row["timestamp"])
        out.append(UsageEvent(**row))
    return out
