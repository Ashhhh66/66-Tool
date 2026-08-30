"""66-Tool — interactive CMD-style privacy hygiene toolkit."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from typing import Any

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from config import load_config
from modules import (
    breach,
    browsers,
    checklist,
    cleaner,
    clipwatch,
    download,
    emailcheck,
    expand,
    fingerprint,
    footprint,
    integrity,
    leaks,
    links,
    passwords,
    posture,
    privacy,
    pwnedpass,
    scrubber,
    secretsfind,
    shredder,
    startup,
    updates,
    wifi,
)
from ui import banner_panel, clear_screen, error, logo_panel, make_console, pause, warn

Runner = Callable[[Console, dict[str, Any], bool], None]

MODULES: dict[str, Runner] = {
    "1": scrubber.run,
    "2": leaks.run,
    "3": shredder.run,
    "4": passwords.run,
    "5": fingerprint.run,
    "6": cleaner.run,
    "7": integrity.run,
    "8": breach.run,
    "9": pwnedpass.run,
    "10": links.run,
    "11": posture.run,
    "12": startup.run,
    "13": emailcheck.run,
    "15": download.run,
    "16": wifi.run,
    "17": clipwatch.run,
    "18": checklist.run,
    "19": privacy.run,
    "20": browsers.run,
    "21": updates.run,
    "22": secretsfind.run,
    "23": expand.run,
    "24": footprint.run,
}


def _require_python() -> None:
    if sys.version_info < (3, 11):
        sys.stderr.write("66-Tool requires Python 3.11 or newer.\n")
        raise SystemExit(2)


def show_help(console: Console) -> None:
    console.print(logo_panel())
    table = Table(title="Tools", show_lines=True)
    table.add_column("Key", style="cyan", width=4)
    table.add_column("Tool")
    table.add_column("What it does")
    rows = (
        ("1", "Metadata Scrubber", "Strip EXIF and PDF metadata before you share a file."),
        ("2", "Network Leak Checker", "Your public IP, DNS resolver hints, VPN/Tor heuristics."),
        ("3", "Secure File Shredder", "Overwrite your files with random data, then delete them."),
        ("4", "Password Generator", "secrets-module passwords and Diceware passphrases."),
        ("5", "Browser Fingerprint Info", "Explain fingerprinting and how to test it in a browser."),
        ("6", "History Cleaner", "Clear YOUR shell history, user temp, and clipboard."),
        ("7", "Integrity Checker", "SHA-256 checksums and verify against a hash you provide."),
        ("8", "Breach Check", "XposedOrNot — your own email only (free, no API key)."),
        ("9", "Password Leak Check", "k-anonymity Pwned Passwords (password never sent in full)."),
        ("10", "Link / Phishing Inspector", "One URL you paste: host, redirects, TLS, shape heuristics."),
        ("11", "PC Security Snapshot", "BitLocker, Defender, firewall, recent hotfixes (read-only)."),
        ("12", "Startup Programs", "Your HKCU Run keys and Startup folder; optional disable."),
        ("13", "Email (.eml) Check", "From / Return-Path / Reply-To mismatch and tracking links."),
        ("15", "Download / Attachment Check", "Magic bytes vs name, Office macros, double extensions."),
        ("16", "Wi-Fi / Network Hygiene", "SSID, WPA vs open, OS DNS, cafe-Wi-Fi reminder."),
        ("17", "Clipboard Watch", "Preview clipboard; watch for URL or crypto-address swaps."),
        ("18", "Account Hardening Checklist", "Your 2FA / unique password / recovery ticks (local file)."),
        ("19", "App Privacy Snapshot", "Camera, mic, location consent for this Windows user."),
        ("20", "Browser Data Cleaner", "Cache / cookies / history in your Chrome, Edge, Brave, Firefox."),
        ("21", "Update Status", "Python, 66-Tool packages vs PyPI, recent Windows hotfixes."),
        ("22", "Secret-in-Files Search", "Scan a folder you own; matches are masked."),
        ("23", "Short Link / QR Expand", "One short URL or QR image to the real destination."),
        ("24", "Personal Footprint", "Public profile URLs / Gravatar for YOUR identifier only."),
        ("h", "Help", "This list plus safety notes. n / p change menu pages."),
    )
    for row in rows:
        table.add_row(*row)
    console.print(table)
    console.print(
        "\n[bold]Safety[/]\n"
        "• Destructive actions need an explicit y confirmation (default is No).\n"
        "• --dry-run previews shred/clean/startup-disable/browser-clean without changing anything.\n"
        "• Only your own files and identifiers. No scanning, exploits, or other users.\n"
        "• Breach check uses the free XposedOrNot API. No paid key required.\n"
        "• SSD/TRIM shredding is best-effort, not a forensic guarantee.\n"
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="66-Tool",
        description=(
            "Personal privacy/security hygiene toolkit. "
            "Local files you own, plus your own public-IP/DNS/HIBP self-checks."
        ),
    )
    parser.add_argument(
        "choice",
        nargs="?",
        help="Optional menu number (1-13, 15-24, h=help) to run once instead of looping",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview destructive actions (shred, clean) without changing files",
    )
    return parser.parse_args(argv)


def run_choice(
    console: Console,
    config: dict[str, Any],
    choice: str,
    *,
    dry_run: bool,
    interactive: bool,
) -> bool:
    """Return False if the user asked to exit."""
    key = choice.strip().lower()
    if key in {"0", "q", "quit", "exit"}:
        console.print("[dim]Goodbye.[/]")
        return False
    if key in {"14", "h", "help"}:
        show_help(console)
        if interactive:
            pause(console)
        return True
    runner = MODULES.get(key)
    if runner is None:
        error(console, "Unknown option. 1-13, 15-24, n/p pages, h help, 0 exit.")
        if interactive:
            pause(console)
        return True
    try:
        runner(console, config, dry_run)
    except KeyboardInterrupt:
        warn(console, "Cancelled.")
    except (PermissionError, ValueError, FileNotFoundError, OSError) as exc:
        error(console, str(exc))
    except Exception as exc:  # noqa: BLE001 — keep the menu alive
        error(console, f"Unexpected error: {exc}")
    if interactive:
        pause(console)
    return True


def menu_loop(console: Console, config: dict[str, Any], dry_run: bool) -> None:
    page = 1
    while True:
        clear_screen()
        console.print(banner_panel(dry_run=dry_run, page=page))
        choice = Prompt.ask("Select", default="")
        key = choice.strip().lower()
        if key in {"n", "next"}:
            page = 2
            continue
        if key in {"p", "prev", "previous", "b", "back"}:
            page = 1
            continue
        if not run_choice(console, config, choice, dry_run=dry_run, interactive=True):
            break


def main(argv: list[str] | None = None) -> int:
    _require_python()
    args = parse_args(argv)
    console = make_console()
    config = load_config()
    if args.choice:
        run_choice(console, config, args.choice, dry_run=args.dry_run, interactive=False)
        return 0
    menu_loop(console, config, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
