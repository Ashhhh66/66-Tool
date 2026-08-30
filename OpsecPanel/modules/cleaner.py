"""Clear the current user's shell history, temp files, and clipboard."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn

from safety import assert_user_path, format_size
from ui import ask_yes_no, confirm_destructive, error, info, warn

HISTORY_CANDIDATES = (
    Path.home() / "AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/ConsoleHost_history.txt",
    Path.home() / "Documents/PowerShell/PSReadLine/ConsoleHost_history.txt",
    Path.home() / "AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/Visual Studio Code Host_history.txt",
    Path.home() / ".bash_history",
    Path.home() / ".zsh_history",
    Path.home() / ".python_history",
    Path.home() / ".local/share/fish/fish_history",
)


def _history_files() -> list[Path]:
    found: list[Path] = []
    for path in HISTORY_CANDIDATES:
        try:
            resolved = assert_user_path(path)
        except PermissionError:
            continue
        if resolved.is_file():
            found.append(resolved)
    return found


def _temp_files(root: Path, limit: int = 50_000) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        dirnames[:] = [d for d in dirnames if not Path(dirpath, d).is_symlink()]
        for name in filenames:
            path = Path(dirpath) / name
            if path.is_symlink():
                continue
            files.append(path)
            if len(files) >= limit:
                return files
    return files


def _clear_history_file(path: Path) -> None:
    path.write_bytes(b"")


def _empty_clipboard() -> str:
    if os.name == "nt":
        import ctypes

        user32 = ctypes.windll.user32
        if not user32.OpenClipboard(None):
            raise OSError("Could not open the clipboard (is another app locking it?).")
        try:
            if not user32.EmptyClipboard():
                raise OSError("EmptyClipboard failed.")
        finally:
            user32.CloseClipboard()
        return "Windows clipboard emptied."
    for cmd in (
        ["pbcopy"],
        ["xclip", "-selection", "clipboard"],
        ["wl-copy"],
    ):
        import subprocess

        try:
            subprocess.run(cmd, input=b"", check=True, timeout=5)
            return f"Clipboard emptied via {cmd[0]}."
        except (OSError, subprocess.SubprocessError):
            continue
    raise OSError("No clipboard helper found (pbcopy / xclip / wl-copy).")


def run(console: Console, config: dict[str, Any], dry_run: bool) -> None:
    _ = config
    info(
        console,
        "Current user only. Never touches other profiles or Windows Event Logs.\n"
        "Each category is confirmed separately (default No).",
    )

    histories = _history_files()
    if ask_yes_no(console, "Review shell / REPL history files?", default=True):
        if not histories:
            warn(console, "No known history files found under your profile.")
        else:
            total = sum(p.stat().st_size for p in histories)
            ok = confirm_destructive(
                console,
                "Truncate these history files to empty (files stay so the shell can keep using them).",
                histories,
                total_bytes=total,
                dry_run=dry_run,
            )
            if ok:
                for path in histories:
                    try:
                        _clear_history_file(path)
                        console.print(f"[green]Cleared[/] {path}")
                    except OSError as exc:
                        error(console, f"{path}: {exc}")

    temp_root = Path(tempfile.gettempdir())
    try:
        temp_root = assert_user_path(temp_root)
    except PermissionError as exc:
        error(console, f"Temp dir refused: {exc}")
        temp_root = None

    if temp_root and ask_yes_no(console, f"Review user temp directory ({temp_root})?", default=False):
        files = _temp_files(temp_root)
        total = 0
        for path in files:
            try:
                total += path.stat().st_size
            except OSError:
                pass
        console.print(f"{len(files)} file(s) in temp ({format_size(total)}). Locked files will be skipped.")
        ok = confirm_destructive(
            console,
            f"Delete files under {temp_root} that this account can unlink. Directories may remain.",
            files,
            total_bytes=total,
            dry_run=dry_run,
        )
        if ok:
            skipped = 0
            deleted = 0
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("Cleaning temp", total=len(files))
                for path in files:
                    try:
                        path.unlink()
                        deleted += 1
                    except OSError:
                        skipped += 1
                    progress.advance(task)
            console.print(f"[green]Deleted {deleted}[/], skipped {skipped} (in use or denied).")

    if ask_yes_no(console, "Clear the clipboard?", default=False):
        if dry_run:
            warn(console, "Dry-run: clipboard would be emptied.")
        elif ask_yes_no(console, "Empty the clipboard now? This cannot be undone.", default=False):
            try:
                console.print(f"[green]{_empty_clipboard()}[/]")
            except OSError as exc:
                error(console, str(exc))
        else:
            console.print("[dim]Clipboard left unchanged.[/]")
