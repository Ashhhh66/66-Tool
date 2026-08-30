"""Persist the last 66-Tool run so the report module can write it up."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .result import OPERATOR, PRODUCT, NOTICE, Result, utc_now

DEFAULT_NAME = ".66-tool-last.json"
MAX_RUNS = 50


def session_path() -> Path:
    override = os.environ.get("TOOL66_SESSION")
    if override:
        return Path(override)
    return Path(DEFAULT_NAME)


def load(path: Path | None = None) -> dict[str, Any] | None:
    target = path or session_path()
    if not target.is_file():
        return None
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("runs"), list):
        return None
    return payload


def record(result: Result, path: Path | None = None) -> Path:
    target = path or session_path()
    current = load(target) or {
        "operator": OPERATOR,
        "product": PRODUCT,
        "notice": NOTICE,
        "runs": [],
    }
    runs = list(current.get("runs") or [])
    runs.append(result.to_payload())
    current["operator"] = OPERATOR
    current["product"] = PRODUCT
    current["notice"] = NOTICE
    current["updated_utc"] = utc_now()
    current["runs"] = runs[-MAX_RUNS:]
    target.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    return target


def clear(path: Path | None = None) -> bool:
    target = path or session_path()
    if not target.exists():
        return False
    target.unlink()
    return True
