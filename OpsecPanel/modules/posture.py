"""Read-only snapshot of this PC's disk encryption, AV, firewall, and updates."""

from __future__ import annotations

import os
import subprocess
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ui import info, warn


def _powershell(command: str, timeout: float = 20.0) -> str:
    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            command,
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )
    out = (completed.stdout or "").strip()
    err = (completed.stderr or "").strip()
    if completed.returncode != 0 and not out:
        raise OSError(err or f"PowerShell exited {completed.returncode}")
    if err and not out:
        return err
    return out or err or "(no output)"


def run(console: Console, config: dict[str, Any], dry_run: bool) -> None:
    _ = config, dry_run
    info(
        console,
        "Read-only checks on THIS machine. Nothing is changed.\n"
        "Some items need Windows; BitLocker details may require elevation.",
    )
    if os.name != "nt":
        warn(console, "This snapshot is written for Windows. On other systems, use your OS security settings.")
        return

    checks: list[tuple[str, str]] = [
        (
            "BitLocker",
            "Get-BitLockerVolume | Select-Object MountPoint, VolumeStatus, ProtectionStatus | Format-List | Out-String",
        ),
        (
            "Microsoft Defender",
            "Get-MpComputerStatus | Select-Object AMServiceEnabled, AntivirusEnabled, "
            "RealTimeProtectionEnabled, IoavProtectionEnabled, NISEnabled, "
            "AntispywareEnabled | Format-List | Out-String",
        ),
        (
            "Firewall profiles",
            "Get-NetFirewallProfile | Select-Object Name, Enabled | Format-Table -AutoSize | Out-String",
        ),
        (
            "Recent hotfixes",
            "Get-HotFix | Sort-Object InstalledOn | Select-Object -Last 8 "
            "HotFixID, Description, InstalledOn | Format-Table -AutoSize | Out-String",
        ),
    ]

    for title, command in checks:
        try:
            body = _powershell(command)
        except (OSError, subprocess.SubprocessError) as exc:
            body = f"(could not read: {exc})"
        console.print(Panel(body.strip() or "(empty)", title=title, border_style="cyan"))

    table = Table(title="How to read this")
    table.add_column("Item")
    table.add_column("Safer if")
    table.add_row("BitLocker ProtectionStatus", "On / Protection On for the system drive")
    table.add_row("Defender RealTimeProtectionEnabled", "True")
    table.add_row("Firewall Enabled", "True on Domain, Private, and Public")
    table.add_row("Hotfixes", "Recent InstalledOn dates (this week / this month)")
    console.print(table)
    console.print(
        "[dim]This is a snapshot, not a pentest. Turn these on in Windows Security if they are off.[/]"
    )
