"""Read-only: Python, this tool's packages, and recent Windows updates."""

from __future__ import annotations

import importlib.metadata
import json
import os
import subprocess
import sys
from typing import Any

from rich.console import Console
from rich.table import Table

from safety import http_get
from ui import info, warn

PACKAGES = ("rich", "PyYAML", "Pillow", "pypdf", "mutagen")


def _installed(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "(not installed)"


def _pypi_version(name: str) -> str:
    status, body, _ = http_get(f"https://pypi.org/pypi/{name}/json", timeout=8.0)
    if status != 200:
        return f"(HTTP {status})"
    data = json.loads(body.decode("utf-8"))
    return str(data.get("info", {}).get("version") or "?")


def _hotfixes() -> str:
    if os.name != "nt":
        return "(Windows only)"
    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "Get-HotFix | Sort-Object InstalledOn | Select-Object -Last 5 "
            "HotFixID, Description, InstalledOn | Format-Table -AutoSize | Out-String",
        ],
        capture_output=True,
        text=True,
        timeout=20,
        encoding="utf-8",
        errors="replace",
    )
    return (completed.stdout or completed.stderr or "(no data)").strip()


def run(console: Console, config: dict[str, Any], dry_run: bool) -> None:
    _ = config, dry_run
    info(console, "Read-only. Compares this app's libraries to PyPI. Does not install anything.")
    table = Table(title="Runtime")
    table.add_column("Item")
    table.add_column("Value")
    table.add_row("Python", sys.version.split()[0])
    if sys.version_info < (3, 11):
        table.add_row("Note", "66-Tool wants 3.11+")
    console.print(table)

    pkgs = Table(title="Packages used by 66-Tool")
    pkgs.add_column("Package")
    pkgs.add_column("Installed")
    pkgs.add_column("PyPI latest")
    behind = 0
    for name in PACKAGES:
        local = _installed(name)
        try:
            latest = _pypi_version(name)
        except (OSError, json.JSONDecodeError) as exc:
            latest = f"(error: {exc})"
        pkgs.add_row(name, local, latest)
        if local not in {"(not installed)"} and latest and not latest.startswith("(") and local != latest:
            behind += 1
    console.print(pkgs)
    if behind:
        warn(console, f"{behind} package(s) differ from PyPI. Update with: pip install -U -r requirements.txt")
    else:
        console.print("[green]Pinned packages match PyPI (or PyPI was unreachable).[/]")

    console.print("[bold]Recent Windows hotfixes[/]")
    console.print(_hotfixes())
    console.print("[dim]OS updates: Settings > Windows Update. This tool does not patch Windows.[/]")
