"""Overwrite files with random data, then delete them. Current user only."""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn
from rich.prompt import IntPrompt

from config import ROOT
from safety import assert_user_path, format_size
from ui import ask_path, confirm_destructive, info, warn

CHUNK = 64 * 1024


def _iter_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        dirnames[:] = [d for d in dirnames if not Path(dirpath, d).is_symlink()]
        for name in filenames:
            path = Path(dirpath) / name
            if path.is_symlink():
                continue
            files.append(path)
    return sorted(files)


def _refuse_self(path: Path) -> None:
    tool = ROOT.resolve()
    resolved = path.resolve()
    if resolved == tool or resolved in tool.parents:
        raise PermissionError("Refusing to shred the 66-Tool install directory.")
    try:
        resolved.relative_to(tool)
        raise PermissionError("Refusing to shred files inside the 66-Tool directory.")
    except ValueError:
        return


def shred_file(path: Path, passes: int) -> None:
    size = path.stat().st_size
    flags = os.O_RDWR
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    fd = os.open(path, flags)
    try:
        for _ in range(passes):
            os.lseek(fd, 0, os.SEEK_SET)
            remaining = size
            while remaining > 0:
                n = min(CHUNK, remaining)
                os.write(fd, secrets.token_bytes(n))
                remaining -= n
            os.fsync(fd)
        if hasattr(os, "ftruncate"):
            os.ftruncate(fd, 0)
            os.fsync(fd)
    finally:
        os.close(fd)
    path.unlink()


def run(console: Console, config: dict[str, Any], dry_run: bool) -> None:
    passes = int(config.get("shred", {}).get("passes", 3))
    info(
        console,
        "Overwrite-then-delete for files you own.\n"
        "On SSDs/TRIM this is best-effort, not a forensic guarantee.\n"
        f"Configured passes: {passes}",
    )
    raw = ask_path(console, "File or folder to shred")
    if not raw:
        warn(console, "No path given.")
        return
    target = assert_user_path(Path(raw))
    if not target.exists():
        raise FileNotFoundError(f"Not found: {target}")
    _refuse_self(target)

    files = _iter_files(target)
    if not files:
        warn(console, "No files found.")
        return
    total = 0
    for path in files:
        try:
            total += path.stat().st_size
        except OSError:
            pass

    try:
        asked = IntPrompt.ask("Overwrite passes", default=passes)
        passes = max(1, int(asked))
    except (TypeError, ValueError):
        pass

    console.print(
        f"[bold]{len(files)}[/] file(s), [bold]{format_size(total)}[/], "
        f"[bold]{passes}[/] pass(es)."
    )
    ok = confirm_destructive(
        console,
        f"Permanently overwrite and delete the items above ({passes} random pass(es)).",
        files,
        total_bytes=total,
        dry_run=dry_run,
    )
    if not ok:
        return

    failed: list[str] = []
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Shredding", total=len(files))
        for path in files:
            try:
                shred_file(path, passes)
            except OSError as exc:
                failed.append(f"{path}: {exc}")
            progress.advance(task)

    if target.is_dir():
        for dirpath, dirnames, filenames in os.walk(target, topdown=False, followlinks=False):
            if not dirnames and not filenames:
                try:
                    Path(dirpath).rmdir()
                except OSError:
                    pass

    if failed:
        warn(console, "Could not shred:\n" + "\n".join(failed[:20]))
    else:
        console.print("[green]Shred complete.[/]")
