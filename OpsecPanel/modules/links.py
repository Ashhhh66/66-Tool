"""Inspect one URL you were sent: host, redirects, TLS, phishing heuristics."""

from __future__ import annotations

import ipaddress
import socket
import ssl
from typing import Any
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener, HTTPSHandler

from rich.console import Console
from rich.table import Table

from safety import USER_AGENT, validate_single_url
from ui import error, info, warn

MAX_HOPS = 8
SUSPECT_BRANDS = (
    "paypal",
    "microsoft",
    "google",
    "apple",
    "amazon",
    "facebook",
    "instagram",
    "whatsapp",
)


class _Recorder(HTTPRedirectHandler):
    max_repeats = MAX_HOPS
    max_redirections = MAX_HOPS

    def __init__(self) -> None:
        super().__init__()
        self.hops: list[tuple[int, str]] = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        parsed = urlparse(newurl)
        if parsed.scheme not in {"http", "https"}:
            return None
        if len(self.hops) >= MAX_HOPS:
            return None
        self.hops.append((int(code), newurl))
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _host_flags(url: str) -> list[str]:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    flags: list[str] = []
    if parsed.username is not None or "@" in (parsed.netloc or ""):
        flags.append("Contains userinfo (@) — classic bait to hide the real host.")
    if not host:
        flags.append("No hostname.")
        return flags
    try:
        ipaddress.ip_address(host)
        flags.append("Hostname is a raw IP address (unusual for a real login page).")
    except ValueError:
        pass
    if host.startswith("xn--") or ".xn--" in host:
        flags.append("Punycode (xn--) host — check the decoded name below.")
    if any(ord(ch) > 127 for ch in host):
        flags.append("Non-ASCII characters in the host (possible lookalike).")
    labels = host.split(".")
    if len(labels) >= 5:
        flags.append("Unusually many subdomain labels.")
    if "-" in host and any(b in host.replace("-", "") for b in ("paypal", "microsoft", "google", "apple")):
        flags.append("Hyphenated host that echoes a well-known brand.")
    for brand in SUSPECT_BRANDS:
        if brand in host and not host.endswith(f".{brand}.com") and host not in {brand, f"www.{brand}.com"}:
            flags.append(f"Host contains “{brand}” but may not be the official domain.")
            break
    if parsed.scheme == "http":
        flags.append("Plain HTTP — credentials and cookies can be visible on the path.")
    return flags


def _idna(host: str) -> str:
    try:
        return host.encode("idna").decode("ascii")
    except (UnicodeError, AttributeError):
        return host


def _flatten_name(entries: Any) -> dict[str, str]:
    out: dict[str, str] = {}
    for rdn in entries or ():
        for key, val in rdn:
            out[str(key)] = str(val)
    return out


def _tls_info(host: str, port: int) -> dict[str, str]:
    ctx = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=10) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as wrapped:
            cert = wrapped.getpeercert() or {}
    subject = _flatten_name(cert.get("subject"))
    issuer = _flatten_name(cert.get("issuer"))
    sans = []
    for kind, value in cert.get("subjectAltName", ()):
        if kind == "DNS":
            sans.append(value)
    return {
        "subject": subject.get("commonName") or ", ".join(subject.values()) or "?",
        "issuer": issuer.get("commonName") or issuer.get("organizationName") or "?",
        "not_before": str(cert.get("notBefore", "?")),
        "not_after": str(cert.get("notAfter", "?")),
        "SAN": ", ".join(sans[:8]) or "(none listed)",
    }


def _fetch(url: str) -> tuple[int, str, list[tuple[int, str]], str]:
    recorder = _Recorder()
    opener = build_opener(recorder, HTTPSHandler())
    req = Request(url, method="GET", headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    try:
        with opener.open(req, timeout=12) as resp:
            status = int(resp.getcode() or 0)
            final = resp.geturl()
            snippet = resp.read(2048).decode("utf-8", "replace")
            return status, final, recorder.hops, snippet
    except Exception as exc:
        if recorder.hops:
            return 0, recorder.hops[-1][1], recorder.hops, str(exc)
        raise


def run(console: Console, config: dict[str, Any], dry_run: bool) -> None:
    _ = config, dry_run
    info(
        console,
        "Paste ONE URL you were sent (email, chat, SMS).\n"
        "This fetches that URL only — no scanning of other hosts.",
    )
    from rich.prompt import Prompt

    raw = Prompt.ask("URL")
    try:
        url = validate_single_url(raw)
    except ValueError as exc:
        error(console, str(exc))
        return

    parsed = urlparse(url)
    host = parsed.hostname or ""
    table = Table(title="URL")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Scheme", parsed.scheme)
    table.add_row("Host", host or "(none)")
    if host:
        table.add_row("IDNA / punycode", _idna(host))
    table.add_row("Path", parsed.path or "/")
    console.print(table)

    flags = _host_flags(url)
    if flags:
        warn(console, "Heuristics (not proof):\n- " + "\n- ".join(flags))
    else:
        console.print("[green]No obvious URL-shape red flags.[/] Still open it only if you trust the sender.")

    try:
        status, final, hops, _snippet = _fetch(url)
        hop_table = Table(title="Redirect chain")
        hop_table.add_column("Step")
        hop_table.add_column("HTTP")
        hop_table.add_column("URL")
        hop_table.add_row("0", "start", url)
        for i, (code, loc) in enumerate(hops, start=1):
            hop_table.add_row(str(i), str(code), loc)
        hop_table.add_row("final", str(status or "?"), final)
        console.print(hop_table)
        start_host = (urlparse(url).hostname or "").lower()
        end_host = (urlparse(final).hostname or "").lower()
        if start_host and end_host and start_host != end_host:
            warn(console, f"Host changed: {start_host} → {end_host}")
    except OSError as exc:
        error(console, f"Fetch failed: {exc}")
        final = url

    final_host = urlparse(final).hostname
    final_scheme = urlparse(final).scheme
    if final_host and final_scheme == "https":
        port = urlparse(final).port or 443
        try:
            cert = _tls_info(final_host, port)
            ct = Table(title=f"TLS certificate for {final_host}")
            ct.add_column("Field")
            ct.add_column("Value")
            for key, val in cert.items():
                ct.add_row(key, val)
            console.print(ct)
        except OSError as exc:
            warn(console, f"Could not read TLS cert: {exc}")
