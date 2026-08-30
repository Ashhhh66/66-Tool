"""Rich console helpers: banner, confirmations, tables, pauses."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from rich import box
from rich.align import Align
from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from safety import format_size

PAGE_1: tuple[tuple[str, str, str], ...] = (
    ("1", "Metadata Scrubber", "Strip EXIF/metadata from images and PDFs"),
    ("2", "Network Leak Checker", "Public IP, DNS leak hints, VPN/Tor status"),
    ("3", "Secure File Shredder", "Overwrite then delete files you own"),
    ("4", "Password Generator", "Cryptographically strong passwords / Diceware"),
    ("5", "Browser Fingerprint Info", "What fingerprinting is and how to check it"),
    ("6", "Local Log / History Cleaner", "Your shell history, temp files, clipboard"),
    ("7", "File Integrity Checker", "SHA-256 generate and verify"),
    ("8", "Breach Check", "Your own email vs XposedOrNot (free, no API key)"),
    ("9", "Password Leak Check", "k-anonymity check vs Pwned Passwords"),
    ("10", "Link / Phishing Inspector", "Inspect one URL you were sent"),
    ("11", "PC Security Snapshot", "BitLocker, Defender, firewall, updates"),
    ("12", "Startup Programs", "Your HKCU Run keys and Startup folder"),
    ("13", "Email (.eml) Check", "Spoof and tracking hints in a saved message"),
)

PAGE_2: tuple[tuple[str, str, str], ...] = (
    ("15", "Download / Attachment Check", "Type vs extension, macros, double-ext tricks"),
    ("16", "Wi-Fi / Network Hygiene", "SSID, encryption, DNS, open-network warning"),
    ("17", "Clipboard Watch", "Show clipboard; watch for URL/address swaps"),
    ("18", "Account Hardening Checklist", "Your 2FA / unique password / recovery ticks"),
    ("19", "App Privacy Snapshot", "Camera, mic, location access for your apps"),
    ("20", "Browser Data Cleaner", "Your Chrome/Edge/Firefox cache and cookies"),
    ("21", "Update Status", "Python, packages, recent Windows hotfixes"),
    ("22", "Secret-in-Files Search", "Scan a folder you own for keys and secrets"),
    ("23", "Short Link / QR Expand", "One short URL or QR image to the real destination"),
    ("24", "Personal Footprint", "Public pages for YOUR handle or email only"),
)

MENU_ITEMS: tuple[tuple[str, str, str], ...] = PAGE_1 + PAGE_2


def make_console() -> Console:
    if os.name == "nt":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass
    return Console(legacy_windows=False)


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


# Big-money ASCII "66" — no Unicode, so Windows CMD never chokes.
_LOGO_SIXES = (
    r"   $$$$$$\   $$$$$$\  ",
    r"  $$  __$$\ $$  __$$\ ",
    r"  $$ /  \__|$$ /  \__|",
    r"  $$$$$$$\  $$$$$$$\  ",
    r"  $$  __$$\ $$  __$$\ ",
    r"  $$ /  $$ |$$ /  $$ |",
    r"   $$$$$$  | $$$$$$  |",
    r"   \______/  \______/ ",
)
_LOGO_ROW_STYLES = (
    "bold bright_cyan",
    "bold bright_cyan",
    "bold cyan",
    "bold bright_white",
    "bold cyan",
    "bold cyan",
    "bold bright_cyan",
    "dim cyan",
)


def _six_line(line: str, style: str, width: int) -> Text:
    padded = line.ljust(width)
    mid = width // 2
    text = Text()
    text.append(padded[:mid], style=style)
    right = "bold magenta" if style.startswith("bold") else "dim magenta"
    text.append(padded[mid:], style=right)
    return text


def logo_panel() -> Panel:
    width = max(len(line) for line in _LOGO_SIXES)
    rows = [
        Align.center(_six_line(line, style, width))
        for line, style in zip(_LOGO_SIXES, _LOGO_ROW_STYLES, strict=True)
    ]
    body = Group(
        *rows,
        Text(""),
        Align.center(Text("T O O L", style="bold bright_white")),
        Align.center(Text("ASHH66", style="bold cyan")),
        Align.center(Text("privacy hygiene  |  your machine only", style="dim")),
    )
    return Panel(
        body,
        box=box.DOUBLE,
        border_style="bright_cyan",
        title="[bold bright_white]*[/] [bold white]66 TOOL[/] [bold bright_white]*[/]",
        subtitle="[dim]Ashh66[/]",
        padding=(1, 3),
    )


def banner_panel(*, dry_run: bool, page: int = 1) -> RenderableType:
    page = 1 if page < 2 else 2
    items = PAGE_1 if page == 1 else PAGE_2
    body = Text()
    body.append("Personal privacy / security hygiene  |  current user only\n", style="dim")
    body.append("No scanning, exploits, or lookups of other people.\n\n")
    for key, title, _blurb in items:
        body.append(f"  {key:>2}  ", style="bold cyan")
        body.append(f"{title}\n")
    body.append("\n")
    if page == 1:
        body.append("   n  ", style="bold magenta")
        body.append("Next page\n")
    else:
        body.append("   p  ", style="bold magenta")
        body.append("Previous page\n")
    body.append("   h  ", style="bold cyan")
    body.append("Help\n")
    body.append("   0  ", style="bold cyan")
    body.append("Exit\n")
    if dry_run:
        body.append("\n  DRY-RUN is on — destructive actions will only be previewed.", style="bold yellow")
    menu = Panel(
        body,
        title=f"[bold white]66 TOOL[/]  [dim]page {page}/2[/]",
        subtitle="number  |  n/p pages  |  q exits",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 2),
    )
    return Group(logo_panel(), menu)


def pause(console: Console) -> None:
    Prompt.ask("\n[dim]Press Enter to return to the menu[/]", default="", show_default=False)


def warn(console: Console, message: str) -> None:
    console.print(Panel(message, title="Notice", border_style="yellow"))


def error(console: Console, message: str) -> None:
    console.print(Panel(message, title="Error", border_style="red"))


def info(console: Console, message: str) -> None:
    console.print(Panel(message, title="Info", border_style="cyan"))


def confirm_destructive(
    console: Console,
    summary: str,
    items: list[Path] | list[str],
    *,
    total_bytes: int | None = None,
    dry_run: bool = False,
) -> bool:
    """Show exactly what will be affected. Default is No. Dry-run never proceeds."""
    table = Table(title="Would be affected" if dry_run else "Will be affected", show_lines=False)
    table.add_column("#", style="dim", width=4)
    table.add_column("Path")
    table.add_column("Size", justify="right")

    display = items[:40]
    for index, item in enumerate(display, start=1):
        path = Path(item) if not isinstance(item, Path) else item
        size = ""
        try:
            if path.is_file():
                size = format_size(path.stat().st_size)
        except OSError:
            size = "?"
        table.add_row(str(index), str(path), size)

    console.print(table)
    extra = len(items) - len(display)
    if extra > 0:
        console.print(f"[dim]… and {extra} more[/]")
    if total_bytes is not None:
        console.print(f"[bold]Total size:[/] {format_size(total_bytes)}  [bold]Count:[/] {len(items)}")
    console.print(f"\n{summary}")

    if dry_run:
        warn(console, "Dry-run: nothing will be overwritten, deleted, or cleared.")
        return False

    answer = Prompt.ask("[bold red]Type y to proceed[/] (anything else cancels)", default="N")
    return answer.strip().lower() in {"y", "yes"}


def ask_path(console: Console, label: str, default: str = "") -> str:
    kwargs: dict = {"default": default} if default else {}
    return Prompt.ask(label, **kwargs).strip().strip('"')


def ask_yes_no(console: Console, label: str, *, default: bool = False) -> bool:
    suffix = "Y/n" if default else "y/N"
    answer = Prompt.ask(f"{label} [{suffix}]", default="Y" if default else "N")
    return answer.strip().lower() in {"y", "yes"}
