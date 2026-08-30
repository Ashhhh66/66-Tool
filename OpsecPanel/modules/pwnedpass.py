"""Check whether a password you type appears in public dumps (k-anonymity)."""

from __future__ import annotations

import getpass
import hashlib
import hmac
from typing import Any

from rich.console import Console
from rich.table import Table

from safety import USER_AGENT, http_get
from ui import error, info, warn

RANGE_URL = "https://api.pwnedpasswords.com/range/{prefix}"


def sha1_hex(password: str) -> str:
    return hashlib.sha1(password.encode("utf-8")).hexdigest().upper()


def lookup_count(digest: str) -> int:
    prefix, suffix = digest[:5], digest[5:]
    status, body, _ = http_get(
        RANGE_URL.format(prefix=prefix),
        headers={
            "User-Agent": USER_AGENT,
            "Add-Padding": "true",
            "Accept": "text/plain",
        },
        timeout=15.0,
    )
    if status != 200:
        raise OSError(f"Pwned Passwords HTTP {status}")
    text = body.decode("utf-8", "replace")
    for line in text.splitlines():
        if not line.strip() or ":" not in line:
            continue
        hashed, _, count_s = line.partition(":")
        if hmac.compare_digest(hashed.strip().upper(), suffix):
            try:
                return max(0, int(count_s.strip()))
            except ValueError:
                return 1
    return 0


def run(console: Console, config: dict[str, Any], dry_run: bool) -> None:
    _ = config, dry_run
    info(
        console,
        "Have I Been Pwned Pwned Passwords uses k-anonymity:\n"
        "this tool SHA-1 hashes locally, then sends only the first 5 hex chars.\n"
        "The password is not stored and is not echoed. Check passwords you use.",
    )
    try:
        password = getpass.getpass("Password (input hidden, not saved): ")
    except (EOFError, KeyboardInterrupt):
        warn(console, "Cancelled.")
        return
    if not password:
        warn(console, "Nothing entered.")
        return
    digest = sha1_hex(password)
    password = ""
    del password
    try:
        count = lookup_count(digest)
    except OSError as exc:
        error(console, str(exc))
        return

    table = Table(title="Pwned Passwords")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("SHA-1 prefix sent", digest[:5] + "…")
    table.add_row("Full hash / password", "never sent, never stored")
    if count:
        table.add_row("Seen in dumps", f"yes — about {count:,} times")
        console.print(table)
        warn(
            console,
            "This password has appeared in public breach data.\n"
            "Stop using it. Change it on every site where it was reused, "
            "and prefer a password manager + unique passphrase.",
        )
    else:
        table.add_row("Seen in dumps", "no matches in this range")
        console.print(table)
        console.print(
            "[green]Not listed[/] in Pwned Passwords right now. "
            "That is not a guarantee it is strong — still use unique passwords."
        )
