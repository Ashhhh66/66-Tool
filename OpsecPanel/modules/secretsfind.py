"""Search a folder you own for likely secrets. Matches are masked."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn
from rich.table import Table

from safety import assert_user_path
from ui import ask_path, info, warn

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".cache",
    "output",
}
SKIP_SUFFIX = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".exe",
    ".dll",
    ".pdf",
    ".zip",
    ".7z",
    ".mp4",
    ".mp3",
    ".woff",
    ".woff2",
}
MAX_FILES = 2500
MAX_BYTES = 1_500_000

PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("GitHub token", re.compile(r"ghp_[A-Za-z0-9]{20,}")),
    ("Stripe live key", re.compile(r"sk_live_[A-Za-z0-9]{8,}")),
    ("HIBP key field", re.compile(r"(?i)hibp[_-]?api[_-]?key\s*[:=]")),
    ("generic api_key", re.compile(r"(?i)api[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}")),
    ("password assignment", re.compile(r"(?i)password\s*[:=]\s*['\"][^'\"]{6,}")),
)


def _mask(text: str) -> str:
    if len(text) <= 8:
        return "****"
    return text[:4] + "..." + text[-2:]


def run(console: Console, config: dict[str, Any], dry_run: bool) -> None:
    _ = config, dry_run
    info(
        console,
        "Scans a folder YOU name. Hits are masked. Other users' trees are refused.\n"
        "This is a hygiene search before you zip or share a project.",
    )
    raw = ask_path(console, "Folder to scan")
    if not raw:
        warn(console, "No path given.")
        return
    root = assert_user_path(Path(raw))
    if not root.is_dir():
        raise FileNotFoundError(f"Not a folder: {root}")

    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            path = Path(dirpath) / name
            if path.suffix.lower() in SKIP_SUFFIX:
                continue
            files.append(path)
            if len(files) >= MAX_FILES:
                break
        if len(files) >= MAX_FILES:
            break

    hits: list[tuple[str, str, str]] = []
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Scanning", total=len(files))
        for path in files:
            try:
                if path.stat().st_size > MAX_BYTES:
                    progress.advance(task)
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                progress.advance(task)
                continue
            for label, pattern in PATTERNS:
                for match in pattern.finditer(text):
                    rel = str(path.relative_to(root))
                    hits.append((rel, label, _mask(match.group(0))))
                    if len(hits) >= 80:
                        break
                if len(hits) >= 80:
                    break
            progress.advance(task)
            if len(hits) >= 80:
                break

    table = Table(title=f"Possible secrets under {root.name}")
    table.add_column("File")
    table.add_column("Kind")
    table.add_column("Masked")
    if hits:
        for file, kind, masked in hits:
            table.add_row(file, kind, masked)
        console.print(table)
        warn(console, "Review these before sharing the folder. False positives happen.")
    else:
        console.print("[green]No pattern hits in the scanned text files.[/]")
    console.print(f"[dim]Scanned {len(files)} file(s).[/]")
