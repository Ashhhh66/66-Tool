"""Read-only camera / microphone / location consent for this Windows user."""

from __future__ import annotations

import os
from typing import Any

from rich.console import Console
from rich.table import Table

from ui import info, warn

STORES = (
    ("webcam", r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\webcam"),
    ("microphone", r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone"),
    ("location", r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location"),
)


def _enum_store(subkey: str) -> list[tuple[str, str]]:
    import winreg

    rows: list[tuple[str, str]] = []
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey)
    except OSError:
        return rows

    def read_value(handle: object, prefix: str) -> None:
        try:
            value, _typ = winreg.QueryValueEx(handle, "Value")  # type: ignore[arg-type]
            rows.append((prefix, str(value)))
        except OSError:
            pass

    try:
        read_value(key, "(store default)")
        index = 0
        while True:
            try:
                name = winreg.EnumKey(key, index)
            except OSError:
                break
            index += 1
            try:
                child = winreg.OpenKey(key, name)
            except OSError:
                continue
            try:
                if name == "NonPackaged":
                    inner = 0
                    while True:
                        try:
                            app = winreg.EnumKey(child, inner)
                        except OSError:
                            break
                        inner += 1
                        try:
                            app_key = winreg.OpenKey(child, app)
                        except OSError:
                            continue
                        try:
                            pretty = app.replace("#", "\\")
                            read_value(app_key, pretty)
                        finally:
                            winreg.CloseKey(app_key)
                else:
                    read_value(child, name)
            finally:
                winreg.CloseKey(child)
    finally:
        winreg.CloseKey(key)
    return rows


def run(console: Console, config: dict[str, Any], dry_run: bool) -> None:
    _ = config, dry_run
    info(
        console,
        "Read-only. Shows what THIS user allowed for camera, mic, and location.\n"
        "Change these in Windows Settings > Privacy.",
    )
    if os.name != "nt":
        warn(console, "This snapshot is Windows-only.")
        return
    for title, path in STORES:
        rows = _enum_store(path)
        table = Table(title=title)
        table.add_column("App / path")
        table.add_column("Consent")
        if rows:
            for app, value in rows[:40]:
                table.add_row(app, value)
        else:
            table.add_row("(none listed)", "")
        console.print(table)
    console.print(
        "[dim]Allow means the app may use that sensor when it asks. "
        "Revoke anything you do not recognize.[/]"
    )
