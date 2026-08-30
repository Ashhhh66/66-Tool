"""Public DNS records for a domain."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from urllib.error import URLError

from .. import dnsproto
from ..http import fetch
from ..result import Result
from ..validate import normalize_domain

RECORD_TYPES = ("A", "AAAA", "MX", "NS", "TXT", "CNAME")
DOH_URL = "https://cloudflare-dns.com/dns-query"


def _answers_from_udp(name: str, timeout: float) -> tuple[str, dict[str, list[str]], str]:
    records: dict[str, list[str]] = {rtype: [] for rtype in RECORD_TYPES}
    status = "NOERROR"

    def lookup(rtype: str) -> tuple[str, dict[str, object]]:
        return rtype, dnsproto.query_udp(name, rtype, timeout)

    with ThreadPoolExecutor(max_workers=len(RECORD_TYPES)) as pool:
        for rtype, parsed in pool.map(lambda item: lookup(item), RECORD_TYPES):
            rcode_name = str(parsed.get("rcode_name") or "")
            if rcode_name == "NXDOMAIN":
                status = "NXDOMAIN"
            answers = parsed.get("answers") or []
            if isinstance(answers, list):
                for item in answers:
                    if not isinstance(item, dict):
                        continue
                    kind = str(item.get("type") or "")
                    data = str(item.get("data") or "")
                    if kind in records and data and data not in records[kind]:
                        records[kind].append(data)
    resolver = "1.1.1.1"
    source = f"DNS/UDP {resolver} (public resolver)"
    return source, records, status


def _answers_from_doh(name: str, timeout: float) -> tuple[str, dict[str, list[str]], str]:
    records: dict[str, list[str]] = {rtype: [] for rtype in RECORD_TYPES}
    status = "NOERROR"

    def lookup(rtype: str) -> tuple[str, dict[str, Any]]:
        url = f"{DOH_URL}?name={name}&type={rtype}"
        response = fetch(
            url,
            timeout,
            headers={"Accept": "application/dns-json"},
        )
        if response.status != 200:
            raise OSError(f"DoH status {response.status}")
        return rtype, json.loads(response.body.decode("utf-8"))

    with ThreadPoolExecutor(max_workers=len(RECORD_TYPES)) as pool:
        for rtype, payload in pool.map(lambda item: lookup(item), RECORD_TYPES):
            code = int(payload.get("Status") or 0)
            if code == 3:
                status = "NXDOMAIN"
            for item in payload.get("Answer") or []:
                if not isinstance(item, dict):
                    continue
                kind = dnsproto.TYPE_NAMES.get(int(item.get("type") or 0), "")
                data = str(item.get("data") or "").strip().strip('"')
                if kind in records and data and data not in records[kind]:
                    records[kind].append(data)
    return "Cloudflare DNS-over-HTTPS", records, status


def lookup(domain: str, timeout: float) -> Result:
    name = normalize_domain(domain)
    source = "DNS/UDP 1.1.1.1 (public resolver)"
    try:
        source, records, status = _answers_from_udp(name, timeout)
    except OSError:
        try:
            source, records, status = _answers_from_doh(name, timeout)
        except (OSError, URLError, json.JSONDecodeError, ValueError) as exc:
            return Result(
                module="dns",
                source=source,
                target=name,
                ok=False,
                error=str(exc),
            )

    found = sum(len(values) for values in records.values())
    ok = status == "NOERROR" and found > 0
    error = None
    if status == "NXDOMAIN":
        error = "NXDOMAIN"
    elif not found:
        error = "no records returned"
    return Result(
        module="dns",
        source=source,
        target=name,
        ok=ok,
        error=error,
        data={"status": status, "records": records},
    )


def format_text(data: dict[str, Any]) -> str:
    lines = [f"status   {data.get('status', '')}"]
    records = data.get("records") or {}
    for rtype in RECORD_TYPES:
        values = records.get(rtype) or []
        if not values:
            lines.append(f"{rtype:<8} (none)")
            continue
        for index, value in enumerate(values):
            label = rtype if index == 0 else ""
            lines.append(f"{label:<8} {value}")
    return "\n".join(lines)
