"""Expand one short URL, or read a QR image you own, then show the destination."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from .links import _fetch, _host_flags
from safety import assert_user_path, validate_single_url
from ui import error, info, warn

SHORTENERS = {
    "bit.ly",
    "t.co",
    "tinyurl.com",
    "goo.gl",
    "ow.ly",
    "is.gd",
    "cutt.ly",
    "rebrand.ly",
    "lnkd.in",
    "buff.ly",
    "rb.gy",
}
IMAGE_SUFFIX = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}


def _decode_qr(path: Path) -> list[str]:
    try:
        import zxingcpp
        from PIL import Image
    except ImportError:
        return []
    image = Image.open(path)
    try:
        found = zxingcpp.read_barcodes(image)
    except TypeError:
        found = zxingcpp.read_barcodes(image.convert("RGB"))
    texts: list[str] = []
    for item in found or []:
        text = getattr(item, "text", None) or str(item)
        if text:
            texts.append(text)
    return texts


def _show_dest(console: Console, url: str) -> None:
    host = (urlparse(url).hostname or "").lower()
    table = Table(title="Starting URL")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("URL", url)
    table.add_row("Host", host or "?")
    if host in SHORTENERS:
        table.add_row("Shortener", "yes - follow redirects to see the real host")
    console.print(table)
    flags = _host_flags(url)
    if flags:
        warn(console, "Heuristics:\n- " + "\n- ".join(flags))
    try:
        status, final, hops, _ = _fetch(url)
    except OSError as exc:
        error(console, f"Fetch failed: {exc}")
        return
    hop = Table(title="Redirects")
    hop.add_column("HTTP")
    hop.add_column("URL")
    hop.add_row("start", url)
    for code, loc in hops:
        hop.add_row(str(code), loc)
    hop.add_row(str(status or "?"), final)
    console.print(hop)
    start = (urlparse(url).hostname or "").lower()
    end = (urlparse(final).hostname or "").lower()
    if start and end and start != end:
        warn(console, f"Real host is {end} (started at {start}).")


def run(console: Console, config: dict[str, Any], dry_run: bool) -> None:
    _ = config, dry_run
    info(
        console,
        "Paste ONE short URL, or a path to a QR image you own.\n"
        "Only that URL / image is read. No crawling of other links.",
    )
    raw = Prompt.ask("URL or image path").strip().strip('"')
    if not raw:
        warn(console, "Nothing entered.")
        return

    path = Path(raw)
    if path.suffix.lower() in IMAGE_SUFFIX and (path.is_file() or "\\" in raw or "/" in raw):
        image = assert_user_path(path)
        if not image.is_file():
            raise FileNotFoundError(f"Not a file: {image}")
        texts = _decode_qr(image)
        if not texts:
            warn(
                console,
                "No QR payload decoded. Optional: pip install zxing-cpp\n"
                "Or type the URL your phone shows after scanning.",
            )
            return
        for text in texts:
            console.print(f"[bold]QR text:[/] {text}")
            if text.lower().startswith(("http://", "https://")):
                try:
                    _show_dest(console, validate_single_url(text))
                except ValueError as exc:
                    error(console, str(exc))
            else:
                console.print("[dim]QR is not an http(s) URL; shown as text only.[/]")
        return

    try:
        url = validate_single_url(raw)
    except ValueError as exc:
        error(console, str(exc))
        return
    _show_dest(console, url)
