"""List public Wayback Machine CDX snapshots for a URL."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import URLError
from urllib.parse import quote

from ..http import fetch
from ..result import Result
from ..validate import validate_public_url

CDX_URL = "https://web.archive.org/cdx/search/cdx"


def parse_cdx(payload: list[Any]) -> list[dict[str, str]]:
    if not payload:
        return []
    header = payload[0] if payload and isinstance(payload[0], list) else []
    keys = [str(item) for item in header] if header else [
        "urlkey",
        "timestamp",
        "original",
        "mimetype",
        "statuscode",
        "digest",
        "length",
    ]
    rows: list[dict[str, str]] = []
    start = 1 if header and header and str(header[0]).isalpha() else 0
    for item in payload[start:]:
        if not isinstance(item, list):
            continue
        row = {keys[index]: str(item[index]) for index in range(min(len(keys), len(item)))}
        if row:
            rows.append(row)
    return rows


def lookup(url: str, timeout: float, limit: int = 25) -> Result:
    target = validate_public_url(url)
    capped = min(max(1, limit), 100)
    query = (
        f"{CDX_URL}?url={quote(target, safe='')}&output=json&limit={capped}"
        "&fl=timestamp,original,statuscode,mimetype,digest"
    )
    try:
        response = fetch(query, timeout, max_bytes=500_000)
    except URLError as exc:
        return Result(
            module="wayback",
            source="Wayback Machine CDX API",
            target=target,
            ok=False,
            error=str(exc.reason if getattr(exc, "reason", None) else exc),
        )
    if response.status != 200:
        return Result(
            module="wayback",
            source="Wayback Machine CDX API",
            target=target,
            ok=False,
            error=f"CDX status {response.status}",
        )
    try:
        payload = json.loads(response.body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        return Result(
            module="wayback",
            source="Wayback Machine CDX API",
            target=target,
            ok=False,
            error=f"CDX returned non-JSON: {exc}",
        )
    if not isinstance(payload, list):
        payload = []
    snapshots = parse_cdx(payload)
    return Result(
        module="wayback",
        source="Wayback Machine CDX API",
        target=target,
        ok=True,
        data={
            "query": query,
            "count": len(snapshots),
            "snapshots": snapshots,
        },
    )


def format_text(data: dict[str, Any]) -> str:
    lines = [f"count    {data.get('count', 0)}", ""]
    snapshots = data.get("snapshots") or []
    if not snapshots:
        lines.append("(none)")
        return "\n".join(lines)
    lines.append(f"{'TIME':<16}{'STATUS':<8}{'TYPE':<18}URL")
    for row in snapshots:
        lines.append(
            f"{row.get('timestamp', ''):<16}"
            f"{row.get('statuscode', ''):<8}"
            f"{row.get('mimetype', ''):<18}"
            f"{row.get('original', '')}"
        )
    return "\n".join(lines)
