"""List this user's startup entries. Optional disable of HKCU Run values only."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from safety import assert_user_path
from ui import ask_yes_no, confirm_destructive, error, info, warn

RUN_PATHS = (
    r"Software\Microsoft\Windows\CurrentVersion\Run",
    r"Software\Microsoft\Windows\CurrentVersion\RunOnce",
)


def _startup_folder() -> Path:
    return Path.home() / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup"


def _enum_hkcu(subkey: str) -> list[tuple[str, str, str]]:
    import winreg

    rows: list[tuple[str, str, str]] = []
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey)
    except OSError:
        return rows
    try:
        index = 0
        while True:
            try:
                name, value, _typ = winreg.EnumValue(key, index)
            except OSError:
                break
            rows.append((subkey, name or "(default)", str(value)))
            index += 1
    finally:
        winreg.CloseKey(key)
    return rows


def _delete_hkcu_value(subkey: str, name: str) -> None:
    import winreg

    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey, 0, winreg.KEY_SET_VALUE)
    try:
        winreg.DeleteValue(key, name)
    finally:
        winreg.CloseKey(key)


def _linux_autostart() -> list[Path]:
    folder = Path.home() / ".config/autostart"
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir() if p.suffix.lower() == ".desktop" and p.is_file())


def run(console: Console, config: dict[str, Any], dry_run: bool) -> None:
    _ = config
    info(
        console,
        "Current user only. HKLM / other users are not touched.\n"
        "Listing is read-only until you explicitly confirm a disable.",
    )

    if os.name != "nt":
        files = _linux_autostart()
        if not files:
            warn(console, "No ~/.config/autostart desktop files found.")
            return
        table = Table(title="~/.config/autostart")
        table.add_column("#", style="dim")
        table.add_column("File")
        for i, path in enumerate(files, start=1):
            table.add_row(str(i), str(path))
        console.print(table)
        return

    rows: list[tuple[str, str, str]] = []
    for path in RUN_PATHS:
        rows.extend(_enum_hkcu(path))

    table = Table(title="HKCU Run / RunOnce")
    table.add_column("#", style="dim", width=4)
    table.add_column("Key")
    table.add_column("Name")
    table.add_column("Command")
    if rows:
        for i, (key, name, command) in enumerate(rows, start=1):
            short_key = key.rsplit("\\", 1)[-1]
            table.add_row(str(i), short_key, name, command)
    else:
        table.add_row("—", "—", "(none)", "")
    console.print(table)

    folder = _startup_folder()
    try:
        folder = assert_user_path(folder)
    except PermissionError as exc:
        error(console, str(exc))
        folder = None

    shortcuts: list[Path] = []
    if folder and folder.is_dir():
        shortcuts = sorted(
            p
            for p in folder.iterdir()
            if p.is_file() and not p.name.startswith(".") and p.name.lower() != "desktop.ini"
        )
    st = Table(title=str(folder) if folder else "Startup folder")
    st.add_column("Name")
    if shortcuts:
        for path in shortcuts:
            st.add_row(path.name)
    else:
        st.add_row("(empty or missing)")
    console.print(st)
    console.print("[dim]Unknown entries are not proof of malware — review names you do not recognize.[/]")

    if not rows:
        return
    if not ask_yes_no(console, "Disable one HKCU Run/RunOnce value?", default=False):
        return
    pick = Prompt.ask("Number to disable", default="").strip()
    try:
        index = int(pick)
        key, name, command = rows[index - 1]
    except (ValueError, IndexError):
        error(console, "Not a valid row number.")
        return
    ok = confirm_destructive(
        console,
        f"Remove HKCU value “{name}” (command: {command}). The program is not uninstalled.",
        [f"HKCU\\{key}\\{name}"],
        dry_run=dry_run,
    )
    if not ok:
        return
    try:
        _delete_hkcu_value(key, name)
        console.print(f"[green]Removed[/] {name} from HKCU.")
    except OSError as exc:
        error(console, str(exc))
