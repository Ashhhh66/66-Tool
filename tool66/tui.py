"""Interactive Command Prompt desk for Ashh66 66-Tool."""

from __future__ import annotations

import os
import sys
from typing import Callable, TextIO

from .dispatch import run_and_record
from .output import print_result
from .result import BANNER, NOTICE

Prompt = Callable[[str], str]

ITEMS: tuple[tuple[str, str], ...] = (
    ("dns", "A / AAAA / MX / NS / TXT / CNAME"),
    ("whois", "Domain registration (port 43)"),
    ("headers", "Public HTTP response headers"),
    ("cert", "TLS dates, issuer, SANs"),
    ("subdomains", "Names from public Certificate Transparency"),
    ("ip", "Reverse DNS + RDAP (no port scan)"),
    ("username", "Public profile URLs (HTTP 200)"),
    ("email", "Syntax, Gravatar, breach-lookup links"),
    ("meta", "EXIF / metadata from a local file"),
    ("wayback", "Public Wayback CDX snapshots"),
    ("report", "JSON + markdown of the last run"),
)

FIELDS: dict[str, tuple[tuple[str, str, bool, str], ...]] = {
    "dns": (("domain", "Domain", True, ""),),
    "whois": (("domain", "Domain", True, ""),),
    "headers": (("url", "URL", True, ""),),
    "cert": (("host", "Host", True, ""), ("port", "Port (blank = 443)", False, "")),
    "subdomains": (("domain", "Domain", True, ""), ("limit", "Limit (blank = 200)", False, "")),
    "ip": (("target", "IP or hostname", True, ""),),
    "username": (("handle", "Handle", True, ""),),
    "email": (("address", "Email", True, ""),),
    "meta": (("path", "Local file path", True, ""),),
    "wayback": (("url", "URL", True, ""), ("limit", "Limit (blank = 25)", False, "")),
    "report": (
        ("out", "Output prefix", False, "66-tool-report"),
        ("clear", "Clear last run instead? (y/N)", False, "n"),
    ),
}


def _clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def _draw_menu(selected: int, stdout: TextIO) -> None:
    stdout.write(f"{BANNER}\n")
    stdout.write(f"notice   {NOTICE}\n")
    stdout.write("desk     Command Prompt  |  arrows + Enter, or type a number  |  q quit\n\n")
    for index, (name, blurb) in enumerate(ITEMS, start=1):
        mark = ">" if index - 1 == selected else " "
        stdout.write(f" {mark} {index:>2}  {name:<12} {blurb}\n")
    stdout.write("\n")
    stdout.flush()


def _read_windows_key() -> str:
    import msvcrt

    key = msvcrt.getwch()
    if key in ("\x00", "\xe0"):
        extra = msvcrt.getwch()
        if extra == "H":
            return "up"
        if extra == "P":
            return "down"
        return ""
    if key in ("\r", "\n"):
        return "enter"
    if key in ("q", "Q"):
        return "quit"
    return key


def pick_module(
    prompt: Prompt,
    stdout: TextIO,
    interactive: bool,
    *,
    clear_screen: bool = True,
) -> str | None:
    selected = 0
    if interactive and os.name == "nt" and sys.stdin.isatty():
        while True:
            if clear_screen:
                _clear()
            _draw_menu(selected, stdout)
            stdout.write("  choice  ")
            stdout.flush()
            key = _read_windows_key()
            if key == "up":
                selected = (selected - 1) % len(ITEMS)
            elif key == "down":
                selected = (selected + 1) % len(ITEMS)
            elif key == "enter":
                return ITEMS[selected][0]
            elif key == "quit":
                return None
            elif key.isdigit():
                number = int(key)
                if 1 <= number <= 9:
                    selected = number - 1
    if clear_screen:
        _clear()
    _draw_menu(selected, stdout)
    raw = prompt("choice  ").strip().lower()
    if raw in {"", "q", "quit"}:
        return None
    if raw.isdigit():
        number = int(raw)
        if 1 <= number <= len(ITEMS):
            return ITEMS[number - 1][0]
    for name, _blurb in ITEMS:
        if raw == name:
            return name
    stdout.write("error: pick a number from the list, or q to quit\n")
    return "__retry__"


def collect_fields(module: str, prompt: Prompt) -> dict[str, object]:
    fields: dict[str, object] = {}
    for name, label, required, default in FIELDS[module]:
        suffix = f" [{default}]" if default else ""
        raw = prompt(f"{label}{suffix}: ").strip()
        if not raw:
            raw = default
        if required and not raw:
            raise ValueError(f"{label} is required")
        if name == "clear":
            fields[name] = raw.lower() in {"y", "yes"}
        elif raw == "":
            continue
        else:
            fields[name] = raw
    timeout_raw = prompt("Timeout seconds [10]: ").strip()
    timeout = float(timeout_raw) if timeout_raw else 10.0
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    fields["timeout"] = timeout
    return fields


def run_lookup(module: str, fields: dict[str, object]):
    timeout = float(fields.pop("timeout"))
    return run_and_record(module, timeout, **fields)


def run_desk(
    prompt: Prompt | None = None,
    stdout: TextIO | None = None,
    *,
    clear_screen: bool | None = None,
) -> int:
    read = prompt or input
    out = stdout or sys.stdout
    interactive = sys.stdin.isatty() and sys.stdout.isatty()
    if clear_screen is None:
        clear_screen = interactive

    while True:
        if clear_screen:
            _clear()
        choice = pick_module(
            read,
            out,
            interactive=interactive and clear_screen,
            clear_screen=clear_screen,
        )
        if choice is None:
            out.write("bye\n")
            return 0
        if choice == "__retry__":
            read("press Enter")
            continue
        try:
            fields = collect_fields(choice, read)
            out.write("\nlooking up public data...\n\n")
            out.flush()
            result = run_lookup(choice, fields)
        except (ValueError, KeyError, EOFError) as exc:
            out.write(f"error: {exc}\n")
            read("press Enter")
            continue
        except OSError as exc:
            out.write(f"error: {exc}\n")
            read("press Enter")
            continue
        print_result(result, as_json=False)
        out.write("\n")
        try:
            read("press Enter")
        except EOFError:
            return 0 if result.ok else 1
    return 0
