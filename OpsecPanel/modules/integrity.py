"""SHA-256 generate and verify for files you own."""

from __future__ import annotations

import hashlib
import hmac
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn, TotalFileSizeColumn
from rich.prompt import Prompt
from rich.table import Table

from config import resolve_output_dir
from safety import assert_user_path
from ui import ask_path, ask_yes_no, error, info, warn

CHUNK = 1024 * 1024


def sha256_file(path: Path, console: Console | None = None) -> str:
    digest = hashlib.sha256()
    size = path.stat().st_size
    if console and size > CHUNK:
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TotalFileSizeColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(f"Hashing {path.name}", total=size)
            with path.open("rb") as handle:
                while True:
                    block = handle.read(CHUNK)
                    if not block:
                        break
                    digest.update(block)
                    progress.advance(task, len(block))
    else:
        with path.open("rb") as handle:
            while True:
                block = handle.read(CHUNK)
                if not block:
                    break
                digest.update(block)
    return digest.hexdigest()


def _normalize_hash(value: str) -> str:
    cleaned = value.strip().lower().replace(" ", "")
    if cleaned.startswith("sha256:"):
        cleaned = cleaned[7:]
    if len(cleaned) != 64 or any(c not in "0123456789abcdef" for c in cleaned):
        raise ValueError("Expected a 64-character SHA-256 hex digest.")
    return cleaned


def run(console: Console, config: dict[str, Any], dry_run: bool) -> None:
    _ = dry_run
    info(console, "Generate or verify a SHA-256 checksum for a file you own.")
    mode = Prompt.ask("Mode: [1] generate  [2] verify", default="1").strip()
    raw = ask_path(console, "File path")
    if not raw:
        warn(console, "No path given.")
        return
    path = assert_user_path(Path(raw))
    if not path.is_file():
        raise FileNotFoundError(f"Not a file: {path}")

    digest = sha256_file(path, console)
    table = Table(title=path.name)
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("SHA-256", digest)
    table.add_row("Path", str(path))
    console.print(table)

    if mode == "2":
        known = Prompt.ask("Known-good SHA-256 hex")
        try:
            expected = _normalize_hash(known)
        except ValueError as exc:
            error(console, str(exc))
            return
        if hmac.compare_digest(digest, expected):
            console.print("[bold green]MATCH[/] — file matches the hash you provided.")
        else:
            console.print("[bold red]MISMATCH[/] — file does not match the hash you provided.")
        return

    if ask_yes_no(console, "Write a .sha256 sidecar under the output directory?", default=False):
        out_dir = resolve_output_dir(config)
        sidecar = out_dir / f"{path.name}.sha256"
        sidecar.write_text(f"{digest}  {path.name}\n", encoding="utf-8")
        console.print(f"[green]Wrote[/] {sidecar}")
