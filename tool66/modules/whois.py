"""Public domain WHOIS lookup (port 43)."""

from __future__ import annotations

import re
import socket
from typing import Any

from ..result import Result
from ..validate import normalize_domain

IANA_WHOIS = "whois.iana.org"
EXTRACT_KEYS = (
    ("registrar", re.compile(r"^\s*Registrar:\s*(?!WHOIS|URL|IANA|Abuse)(.+)$", re.I | re.M)),
    ("created", re.compile(r"^\s*(?:Creation Date|created|Created On):\s*(.+)$", re.I | re.M)),
    ("updated", re.compile(r"^\s*(?:Updated Date|last-modified|Last Updated On):\s*(.+)$", re.I | re.M)),
    ("expires", re.compile(r"^\s*(?:Registry Expiry Date|Expiry Date|expires):\s*(.+)$", re.I | re.M)),
)
REFERRAL_RE = re.compile(
    r"^\s*(?:whois|Registrar WHOIS Server|ReferralServer):\s*(?:whois://)?(\S+)",
    re.I | re.M,
)


def query_whois(server: str, query: str, timeout: float) -> str:
    host = server.strip().removeprefix("whois://").split(":")[0]
    chunks: list[bytes] = []
    with socket.create_connection((host, 43), timeout=timeout) as sock:
        sock.settimeout(timeout)
        sock.sendall(query.encode("ascii", errors="replace") + b"\r\n")
        while True:
            piece = sock.recv(4096)
            if not piece:
                break
            chunks.append(piece)
            if sum(len(item) for item in chunks) > 200_000:
                break
    return b"".join(chunks).decode("utf-8", errors="replace")


def _referral(text: str) -> str | None:
    match = REFERRAL_RE.search(text)
    if not match:
        return None
    return match.group(1).strip().rstrip("/")


def lookup_text(domain: str, timeout: float) -> tuple[str, str]:
    name = normalize_domain(domain)
    tld = name.rsplit(".", 1)[-1]
    seen: list[str] = []
    server = IANA_WHOIS
    text = ""
    for _ in range(4):
        if server in seen:
            break
        seen.append(server)
        query = tld if server == IANA_WHOIS else name
        text = query_whois(server, query, timeout)
        referral = _referral(text)
        if not referral or referral in seen:
            break
        server = referral
    return " -> ".join(seen), text


def lookup(domain: str, timeout: float) -> Result:
    name = normalize_domain(domain)
    try:
        chain, text = lookup_text(name, timeout)
    except OSError as exc:
        return Result(
            module="whois",
            source=f"WHOIS port 43 ({IANA_WHOIS})",
            target=name,
            ok=False,
            error=str(exc),
        )
    if not text.strip():
        return Result(
            module="whois",
            source=f"WHOIS port 43 ({chain})",
            target=name,
            ok=False,
            error="empty WHOIS response",
        )
    extracted: dict[str, str] = {}
    for key, pattern in EXTRACT_KEYS:
        match = pattern.search(text)
        if match:
            extracted[key] = match.group(1).strip()
    nameservers = re.findall(
        r"^\s*(?:Name Server|nserver):\s*(\S+)", text, flags=re.I | re.M
    )
    return Result(
        module="whois",
        source=f"WHOIS port 43 ({chain})",
        target=name,
        ok=True,
        data={
            "servers": chain,
            "extracted": extracted,
            "name_servers": nameservers,
            "record": text.strip(),
        },
    )


def format_text(data: dict[str, Any]) -> str:
    lines = [f"servers  {data.get('servers', '')}"]
    extracted = data.get("extracted") or {}
    for key in ("registrar", "created", "updated", "expires"):
        if key in extracted:
            lines.append(f"{key:<8} {extracted[key]}")
    servers = data.get("name_servers") or []
    if servers:
        lines.append(f"ns       {', '.join(servers)}")
    lines.append("")
    lines.append(str(data.get("record") or ""))
    return "\n".join(lines)
