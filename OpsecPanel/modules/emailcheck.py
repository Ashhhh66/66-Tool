"""Inspect a saved .eml for spoofing and tracking-link hints."""

from __future__ import annotations

import re
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from rich.console import Console
from rich.table import Table

from safety import assert_user_path
from ui import ask_path, error, info, warn

HREF_RE = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.I)
URL_RE = re.compile(r"https?://[^\s<>\"']+", re.I)
TRACK_HINTS = ("utm_", "click.", "track", "open?token", "list-manage", "beacon")


def _domain(addr: str) -> str:
    _, email_addr = parseaddr(addr or "")
    if "@" not in email_addr:
        return ""
    return email_addr.rsplit("@", 1)[-1].lower().strip(">")


def _auth_bits(msg) -> str:  # type: ignore[no-untyped-def]
    parts: list[str] = []
    for header in ("Authentication-Results", "Received-SPF", "ARC-Authentication-Results"):
        values = msg.get_all(header) or []
        for value in values:
            parts.append(f"{header}: {value[:200]}")
    if msg.get("DKIM-Signature"):
        parts.append("DKIM-Signature: present")
    return "\n".join(parts) if parts else "(none in this file)"


def _body_text(msg) -> str:  # type: ignore[no-untyped-def]
    chunks: list[str] = []
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype in {"text/plain", "text/html"}:
                try:
                    chunks.append(part.get_content())
                except Exception:
                    payload = part.get_payload(decode=True) or b""
                    chunks.append(payload.decode("utf-8", "replace"))
    else:
        try:
            chunks.append(msg.get_content())
        except Exception:
            payload = msg.get_payload(decode=True) or b""
            chunks.append(payload.decode("utf-8", "replace"))
    return "\n".join(str(c) for c in chunks if c)


def _links(body: str) -> list[str]:
    found: list[str] = []
    for match in HREF_RE.findall(body):
        found.append(match)
    for match in URL_RE.findall(body):
        found.append(match)
    uniq: list[str] = []
    seen: set[str] = set()
    for url in found:
        if url not in seen:
            seen.add(url)
            uniq.append(url)
    return uniq[:40]


def run(console: Console, config: dict[str, Any], dry_run: bool) -> None:
    _ = config, dry_run
    info(
        console,
        "Analyze a message you saved from YOUR mailbox (.eml / .eml.txt).\n"
        "This does not send mail or look up other people.",
    )
    raw = ask_path(console, "Path to .eml file")
    if not raw:
        warn(console, "No path given.")
        return
    path = assert_user_path(Path(raw))
    if not path.is_file():
        raise FileNotFoundError(f"Not a file: {path}")

    msg = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    frm = str(msg.get("From") or "")
    sender = str(msg.get("Sender") or "")
    reply_to = str(msg.get("Reply-To") or "")
    return_path = str(msg.get("Return-Path") or "")
    subject = str(msg.get("Subject") or "")

    hdr = Table(title=path.name)
    hdr.add_column("Header")
    hdr.add_column("Value")
    hdr.add_row("Subject", subject[:200] or "(none)")
    hdr.add_row("From", frm[:240] or "(none)")
    hdr.add_row("Sender", sender[:240] or "(none)")
    hdr.add_row("Reply-To", reply_to[:240] or "(none)")
    hdr.add_row("Return-Path", return_path[:240] or "(none)")
    console.print(hdr)

    from_dom = _domain(frm)
    reply_dom = _domain(reply_to)
    return_dom = _domain(return_path)
    sender_dom = _domain(sender)
    flags: list[str] = []
    display_name, from_addr = parseaddr(frm)
    if from_dom and return_dom and from_dom != return_dom:
        flags.append(f"From domain ({from_dom}) does not match Return-Path domain ({return_dom}).")
    if from_dom and reply_dom and from_dom != reply_dom:
        flags.append(f"Reply-To domain ({reply_dom}) differs from From ({from_dom}).")
    if sender_dom and from_dom and sender_dom != from_dom:
        flags.append(f"Sender domain ({sender_dom}) differs from From ({from_dom}).")
    if display_name and "@" in display_name:
        shown = display_name.lower()
        if from_dom and from_dom not in shown:
            flags.append("Display name includes an email/domain that does not match From.")

    console.print("[bold]Authentication headers[/]")
    console.print(_auth_bits(msg))

    body = _body_text(msg)
    links = _links(body)
    mismatch_hosts: list[str] = []
    if links:
        lt = Table(title="Links in the message (first 40)")
        lt.add_column("Host")
        lt.add_column("URL")
        for url in links:
            host = urlparse(url).hostname or "(relative/odd)"
            mark = "  [track?]" if any(h in url.lower() for h in TRACK_HINTS) else ""
            lt.add_row(str(host) + mark, url[:120])
            if (
                from_dom
                and host
                and host != "(relative/odd)"
                and from_dom not in host.lower()
                and url.lower().startswith("http")
            ):
                if host not in mismatch_hosts:
                    mismatch_hosts.append(host)
        console.print(lt)
        if mismatch_hosts:
            flags.append("Body links point at other hosts: " + ", ".join(mismatch_hosts[:8]))
    else:
        console.print("[dim]No http(s) links found in the body.[/]")

    # de-dupe flags while keeping order
    uniq_flags: list[str] = []
    seen_f: set[str] = set()
    for item in flags:
        if item not in seen_f:
            seen_f.add(item)
            uniq_flags.append(item)
    if uniq_flags:
        warn(console, "Spoof / mismatch hints (not proof):\n- " + "\n- ".join(uniq_flags[:15]))
    else:
        console.print(
            "[green]No obvious From/Reply-To/Return-Path mismatch.[/] "
            "Still treat unexpected attachments and logins with care."
        )
