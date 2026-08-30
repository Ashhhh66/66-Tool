"""Shared result envelope for every 66-Tool module."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

OPERATOR = "Ashh66"
PRODUCT = "66-Tool"
BANNER = "Ashh66 66-Tool"
NOTICE = "public data only"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


@dataclass
class Result:
    module: str
    source: str
    target: str
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    timestamp_utc: str = field(default_factory=utc_now)

    def to_payload(self) -> dict[str, Any]:
        return {
            "operator": OPERATOR,
            "product": PRODUCT,
            "module": self.module,
            "source": self.source,
            "timestamp_utc": self.timestamp_utc,
            "notice": NOTICE,
            "target": self.target,
            "ok": self.ok,
            "error": self.error,
            "data": self.data,
        }
