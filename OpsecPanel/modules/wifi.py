"""Current Wi-Fi / LAN hygiene for this machine only."""

from __future__ import annotations

import os
import subprocess
from typing import Any

from rich.console import Console
from rich.table import Table

from .leaks import _system_dns_servers
from ui import info, warn


def _netsh(args: list[str]) -> str:
    completed = subprocess.run(
        ["netsh", *args],
        capture_output=True,
        text=True,
        timeout=12,
        encoding="oem",
        errors="replace",
    )
    return (completed.stdout or "") + (completed.stderr or "")


def _parse_wlan(text: str) -> dict[str, str]:
    wanted = {
        "ssid": "ssid",
        "state": "state",
        "radio type": "radio",
        "authentication": "auth",
        "cipher": "cipher",
        "signal": "signal",
        "profile": "profile",
    }
    found: dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        norm = key.strip().lower()
        if norm in wanted and val.strip() and wanted[norm] not in found:
            found[wanted[norm]] = val.strip()
    return found


def run(console: Console, config: dict[str, Any], dry_run: bool) -> None:
    _ = config, dry_run
    info(
        console,
        "Shows THIS machine's Wi-Fi / DNS only.\n"
        "No scanning of other clients or nearby networks.",
    )
    table = Table(title="Network hygiene")
    table.add_column("Field")
    table.add_column("Value")

    if os.name == "nt":
        raw = _netsh(["wlan", "show", "interfaces"])
        parsed = _parse_wlan(raw)
        if parsed:
            table.add_row("SSID", parsed.get("ssid", "?"))
            table.add_row("State", parsed.get("state", "?"))
            table.add_row("Authentication", parsed.get("auth", "?"))
            table.add_row("Cipher", parsed.get("cipher", "?"))
            table.add_row("Signal", parsed.get("signal", "?"))
        else:
            table.add_row("Wi-Fi", "No WLAN interface data (Ethernet-only, or Wi-Fi off).")
        auth = (parsed.get("auth") or "").lower()
        if parsed.get("ssid") and ("open" in auth or auth in {"", "none"}):
            warn(
                console,
                "This looks like an open / unencrypted Wi-Fi network.\n"
                "Avoid banking or passwords unless the VPN is on. Prefer mobile data.",
            )
        elif "wpa" in auth or "sae" in auth:
            console.print("[green]Wi-Fi reports WPA/SAE.[/] Still treat public networks as hostile.")
    else:
        table.add_row("Wi-Fi", "Use your OS network settings (this helper is Windows-first).")

    servers = _system_dns_servers()
    table.add_row("OS DNS", ", ".join(servers) if servers else "(unknown)")
    console.print(table)
    if any(s.startswith("192.168.") or s.startswith("10.") or s.startswith("172.") for s in servers):
        console.print(
            "[dim]DNS is a LAN/router address. On untrusted Wi-Fi that is often the venue's DNS. "
            "A trusted VPN should replace these.[/]"
        )
    console.print("[dim]Cross-check with menu 2 (Network Leak Checker) if a VPN should be on.[/]")
