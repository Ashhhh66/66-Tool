"""Reverse DNS plus public RDAP registration data. No port scan."""

from __future__ import annotations

import ipaddress
import json
import socket
from typing import Any
from urllib.error import URLError

from ..http import fetch
from ..result import Result
from ..validate import parse_ip

RDAP_URL = "https://rdap.org/ip/{ip}"


def reverse_dns(ip: str) -> str | None:
    try:
        name, _aliases, _addrs = socket.gethostbyaddr(ip)
    except (socket.herror, socket.gaierror, OSError):
        return None
    return name


def _rdap_summary(payload: dict[str, Any]) -> dict[str, Any]:
    entities = []
    for item in payload.get("entities") or []:
        if not isinstance(item, dict):
            continue
        vcard = item.get("vcardArray")
        name = None
        if isinstance(vcard, list) and len(vcard) > 1:
            for row in vcard[1]:
                if isinstance(row, list) and row and row[0] == "fn" and len(row) >= 4:
                    name = row[3]
        entities.append(
            {
                "handle": item.get("handle"),
                "roles": item.get("roles") or [],
                "name": name,
            }
        )
    cidrs = []
    for item in payload.get("cidr0_cidrs") or []:
        if isinstance(item, dict) and item.get("v4prefix"):
            cidrs.append(f"{item['v4prefix']}/{item.get('length')}")
        elif isinstance(item, dict) and item.get("v6prefix"):
            cidrs.append(f"{item['v6prefix']}/{item.get('length')}")
    return {
        "handle": payload.get("handle"),
        "name": payload.get("name"),
        "type": payload.get("type"),
        "country": payload.get("country"),
        "start_address": payload.get("startAddress"),
        "end_address": payload.get("endAddress"),
        "cidrs": cidrs,
        "entities": entities,
        "rdap_url": (payload.get("links") or [{}])[0].get("href")
        if payload.get("links")
        else None,
    }


def lookup(target: str, timeout: float) -> Result:
    text = target.strip()
    try:
        ip = parse_ip(text)
    except ValueError:
        try:
            infos = socket.getaddrinfo(text, None)
        except socket.gaierror as exc:
            return Result(
                module="ip",
                source="reverse DNS + RDAP",
                target=text,
                ok=False,
                error=str(exc),
            )
        ip = infos[0][4][0]
        ipaddress.ip_address(ip)

    source = "reverse DNS + RDAP (rdap.org)"
    ptr = reverse_dns(ip)
    rdap: dict[str, Any] | None = None
    rdap_error = None
    try:
        response = fetch(RDAP_URL.format(ip=ip), timeout, max_bytes=200_000)
        if response.status == 200:
            payload = json.loads(response.body.decode("utf-8"))
            if isinstance(payload, dict):
                rdap = _rdap_summary(payload)
        else:
            rdap_error = f"RDAP status {response.status}"
    except (URLError, json.JSONDecodeError, ValueError) as exc:
        rdap_error = str(exc)

    ok = ptr is not None or rdap is not None
    return Result(
        module="ip",
        source=source,
        target=ip,
        ok=ok,
        error=None if ok else (rdap_error or "no reverse DNS or RDAP data"),
        data={
            "ip": ip,
            "queried": text,
            "reverse_dns": ptr,
            "rdap": rdap,
            "rdap_error": rdap_error,
            "note": "No port scan. Use Port-Scanner on hosts you are allowed to test.",
        },
    )


def format_text(data: dict[str, Any]) -> str:
    lines = [
        f"ip       {data.get('ip', '')}",
        f"ptr      {data.get('reverse_dns') or '(none)'}",
    ]
    rdap = data.get("rdap") or {}
    if rdap:
        lines.append(f"net      {rdap.get('name') or ''}")
        lines.append(f"country  {rdap.get('country') or ''}")
        if rdap.get("cidrs"):
            lines.append(f"cidr     {', '.join(rdap['cidrs'])}")
        names = [item.get("name") for item in rdap.get("entities") or [] if item.get("name")]
        if names:
            lines.append(f"org      {', '.join(str(name) for name in names)}")
    elif data.get("rdap_error"):
        lines.append(f"rdap     {data['rdap_error']}")
    lines.append(f"note     {data.get('note', '')}")
    return "\n".join(lines)
