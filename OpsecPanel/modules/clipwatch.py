"""Show the clipboard and optionally watch for URL or address swaps."""

from __future__ import annotations

import os
import re
import time
from typing import Any

from rich.console import Console
from rich.table import Table

from .cleaner import _empty_clipboard
from ui import ask_yes_no, error, info, warn

URL_RE = re.compile(r"https?://[^\s]+", re.I)
ETH_RE = re.compile(r"\b0x[a-fA-F0-9]{40}\b")
BTC_RE = re.compile(r"\b(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}\b")


def read_clipboard() -> str:
    if os.name == "nt":
        import ctypes

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        cf_unicode = 13
        if not user32.OpenClipboard(None):
            raise OSError("Could not open the clipboard.")
        try:
            handle = user32.GetClipboardData(cf_unicode)
            if not handle:
                return ""
            locked = kernel32.GlobalLock(handle)
            if not locked:
                return ""
            try:
                return ctypes.wstring_at(locked)
            finally:
                kernel32.GlobalUnlock(handle)
        finally:
            user32.CloseClipboard()
    try:
        import subprocess

        return subprocess.check_output(["pbpaste"], text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return ""


def _kind(text: str) -> str:
    kinds: list[str] = []
    if URL_RE.search(text):
        kinds.append("URL")
    if ETH_RE.search(text) or BTC_RE.search(text):
        kinds.append("crypto-looking address")
    return ", ".join(kinds) or "text"


def _preview(text: str) -> str:
    compact = " ".join(text.split())
    if len(compact) > 160:
        return compact[:157] + "..."
    return compact or "(empty)"


def run(console: Console, config: dict[str, Any], dry_run: bool) -> None:
    _ = config
    info(console, "Reads YOUR clipboard only. Watch mode looks for sudden URL/address swaps.")
    try:
        current = read_clipboard()
    except OSError as exc:
        error(console, str(exc))
        return

    table = Table(title="Clipboard now")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Kind", _kind(current))
    table.add_row("Preview", _preview(current))
    table.add_row("Length", str(len(current)))
    console.print(table)
    if "crypto" in _kind(current).lower() or _kind(current) == "URL":
        console.print(
            "[yellow]If you just copied this from a site, look at it before you paste. "
            "Clipboard-stealing malware swaps addresses.[/]"
        )

    if ask_yes_no(console, "Watch 20 seconds for a swap?", default=False):
        console.print("[dim]Copy something, or wait. Ctrl+C cancels.[/]")
        start = time.monotonic()
        last = current
        try:
            while time.monotonic() - start < 20:
                time.sleep(0.4)
                now = read_clipboard()
                if now != last:
                    console.print("[bold red]Clipboard changed[/]")
                    nxt = Table()
                    nxt.add_column("When")
                    nxt.add_column("Kind")
                    nxt.add_column("Preview")
                    nxt.add_row("before", _kind(last), _preview(last))
                    nxt.add_row("after", _kind(now), _preview(now))
                    console.print(nxt)
                    if _kind(last) != _kind(now) or (
                        ("URL" in _kind(last) or "crypto" in _kind(last)) and now != last
                    ):
                        warn(console, "This may be a swap. Do not paste until you re-copy from the real source.")
                    last = now
                    current = now
        except KeyboardInterrupt:
            warn(console, "Watch stopped.")

    if ask_yes_no(console, "Empty the clipboard?", default=False):
        if dry_run:
            warn(console, "Dry-run: clipboard would be emptied.")
        elif ask_yes_no(console, "Empty it now?", default=False):
            try:
                console.print(f"[green]{_empty_clipboard()}[/]")
            except OSError as exc:
                error(console, str(exc))
