"""Hostnames published in public Certificate Transparency logs."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import URLError
from urllib.parse import quote

from ..http import fetch
from ..result import Result
from ..validate import normalize_domain

CRT_SH = "https://crt.sh/"
CERTSPOTTER = "https://api.certspotter.com/v1/issuances"
NOTE = "Names as published in public CT logs. 66-Tool does not probe these hosts."


def _keep(name: str, domain: str) -> str | None:
    cleaned = name.strip().lower().rstrip(".")
    if cleaned.startswith("*."):
        cleaned = cleaned[2:]
    if cleaned == domain or cleaned.endswith("." + domain):
        return cleaned
    return None


def names_from_crtsh(records: list[Any], domain: str) -> list[str]:
    found: set[str] = set()
    for item in records:
        if not isinstance(item, dict):
            continue
        raw = str(item.get("name_value") or "")
        for piece in raw.replace(",", "\n").splitlines():
            kept = _keep(piece, domain)
            if kept:
                found.add(kept)
    return sorted(found)


def names_from_certspotter(records: list[Any], domain: str) -> list[str]:
    found: set[str] = set()
    for item in records:
        if not isinstance(item, dict):
            continue
        for piece in item.get("dns_names") or []:
            kept = _keep(str(piece), domain)
            if kept:
                found.add(kept)
    return sorted(found)


def _load_json_list(body: bytes) -> list[Any]:
    payload = json.loads(body.decode("utf-8"))
    return payload if isinstance(payload, list) else []


def lookup(domain: str, timeout: float, limit: int = 200) -> Result:
    name = normalize_domain(domain)
    crt_url = f"{CRT_SH}?q={quote('%.' + name)}&output=json"
    errors: list[str] = []

    try:
        response = fetch(crt_url, timeout, max_bytes=2_000_000)
        if response.status == 200:
            names = names_from_crtsh(_load_json_list(response.body), name)
            clipped = names[: max(1, limit)]
            return Result(
                module="subdomains",
                source="Certificate Transparency via crt.sh",
                target=name,
                ok=True,
                data={
                    "query": crt_url,
                    "names": clipped,
                    "count": len(clipped),
                    "available": len(names),
                    "note": NOTE,
                },
            )
        errors.append(f"crt.sh status {response.status}")
    except (URLError, json.JSONDecodeError, ValueError) as exc:
        errors.append(str(getattr(exc, "reason", exc)))

    spot_url = (
        f"{CERTSPOTTER}?domain={quote(name)}&include_subdomains=true&expand=dns_names"
    )
    try:
        response = fetch(spot_url, timeout, max_bytes=2_000_000)
        if response.status == 200:
            names = names_from_certspotter(_load_json_list(response.body), name)
            clipped = names[: max(1, limit)]
            return Result(
                module="subdomains",
                source="Certificate Transparency via Cert Spotter",
                target=name,
                ok=True,
                data={
                    "query": spot_url,
                    "names": clipped,
                    "count": len(clipped),
                    "available": len(names),
                    "note": NOTE,
                },
            )
        errors.append(f"Cert Spotter status {response.status}")
    except (URLError, json.JSONDecodeError, ValueError) as exc:
        errors.append(str(getattr(exc, "reason", exc)))

    return Result(
        module="subdomains",
        source="Certificate Transparency (crt.sh, Cert Spotter)",
        target=name,
        ok=False,
        error="; ".join(errors) or "no public CT data",
    )


def format_text(data: dict[str, Any]) -> str:
    lines = [
        f"count    {data.get('count', 0)} of {data.get('available', 0)}",
        f"note     {data.get('note', '')}",
        "",
    ]
    names = data.get("names") or []
    if not names:
        lines.append("(none)")
    else:
        lines.extend(str(name) for name in names)
    return "\n".join(lines)
