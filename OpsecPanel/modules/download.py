"""Check a file you downloaded: real type vs name, macros, double extensions."""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from .integrity import sha256_file
from safety import assert_user_path, format_size
from ui import ask_path, info, warn

MAGIC: tuple[tuple[bytes, str], ...] = (
    (b"MZ", "Windows PE / EXE / DLL"),
    (b"%PDF", "PDF"),
    (b"\x89PNG", "PNG image"),
    (b"GIF8", "GIF image"),
    (b"\xff\xd8\xff", "JPEG image"),
    (b"PK\x03\x04", "ZIP / Office Open XML"),
    (b"Rar!\x1a", "RAR archive"),
    (b"7z\xbc\xaf", "7-Zip archive"),
    (b"\xd0\xcf\x11\xe0", "Old Office OLE document"),
    (b"#!", "Script with shebang"),
)

RISKY_EXT = {
    ".exe",
    ".dll",
    ".scr",
    ".com",
    ".bat",
    ".cmd",
    ".ps1",
    ".vbs",
    ".js",
    ".jse",
    ".wsf",
    ".hta",
    ".msi",
    ".msp",
    ".lnk",
    ".iso",
    ".img",
}

MACRO_NAMES = (
    "word/vbaProject.bin",
    "xl/vbaProject.bin",
    "ppt/vbaProject.bin",
)


def _sniff(path: Path) -> str:
    head = path.read_bytes()[:16]
    for magic, label in MAGIC:
        if head.startswith(magic):
            return label
    if not head:
        return "empty file"
    return "unknown / not a common signature"


def _double_ext(name: str) -> bool:
    parts = Path(name).name.split(".")
    return len(parts) >= 3 and f".{parts[-1].lower()}" in RISKY_EXT


def _macros(path: Path) -> list[str]:
    found: list[str] = []
    try:
        with zipfile.ZipFile(path) as zf:
            names = {item.filename.replace("\\", "/") for item in zf.infolist()}
            for item in MACRO_NAMES:
                if item in names:
                    found.append(item)
            if any(n.lower().endswith("vbaproject.bin") for n in names):
                if not found:
                    found.append("vbaProject.bin")
    except zipfile.BadZipFile:
        return []
    return found


def run(console: Console, config: dict[str, Any], dry_run: bool) -> None:
    _ = config, dry_run
    info(
        console,
        "Inspect a file YOU downloaded or were sent.\n"
        "The file is not executed. Close it if a viewer already has it open.",
    )
    raw = ask_path(console, "File path")
    if not raw:
        warn(console, "No path given.")
        return
    path = assert_user_path(Path(raw))
    if not path.is_file():
        raise FileNotFoundError(f"Not a file: {path}")

    sniffed = _sniff(path)
    suffix = path.suffix.lower()
    digest = sha256_file(path, console)
    flags: list[str] = []
    if _double_ext(path.name):
        flags.append("Double extension ending in a runnable type (classic bait).")
    if suffix in RISKY_EXT:
        flags.append(f"Extension {suffix} can run code if you open it.")
    if sniffed.startswith("Windows PE") and suffix not in {".exe", ".dll", ".scr", ".com", ".msi"}:
        flags.append("Looks like a Windows program but the name does not say so.")
    if sniffed.startswith("ZIP") and suffix in {".docx", ".xlsx", ".pptx", ".docm", ".xlsm", ".pptm"}:
        macros = _macros(path)
        if macros:
            flags.append("Office package contains VBA macros: " + ", ".join(macros))
    if sniffed.startswith("Old Office"):
        flags.append("Legacy Office format can carry macros. Prefer asking for a PDF.")

    table = Table(title=path.name)
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Size", format_size(path.stat().st_size))
    table.add_row("Extension", suffix or "(none)")
    table.add_row("Detected type", sniffed)
    table.add_row("SHA-256", digest)
    console.print(table)
    if flags:
        warn(console, "Flags (not proof of malware):\n- " + "\n- ".join(flags))
    else:
        console.print("[green]No obvious name/type tricks.[/] Still only open files you expected.")
