"""Strip EXIF and document metadata from JPEG, PNG, and PDF files you own."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn
from rich.table import Table

from config import resolve_output_dir
from safety import assert_user_path, format_size
from ui import ask_path, ask_yes_no, confirm_destructive, error, info, warn

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
PDF_SUFFIXES = {".pdf"}
SUPPORTED = IMAGE_SUFFIXES | PDF_SUFFIXES
TECHNICAL_KEYS = {
    "format",
    "size",
    "pages",
    "jfif",
    "jfif_version",
    "jfif_unit",
    "jfif_density",
    "dpi",
    "aspect",
}


def _collect(target: Path) -> list[Path]:
    if target.is_file():
        if target.suffix.lower() not in SUPPORTED:
            raise ValueError(f"Unsupported type: {target.suffix} (use JPEG, PNG, or PDF)")
        return [target]
    files = sorted(
        p for p in target.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED
    )
    if not files:
        raise FileNotFoundError(f"No JPEG/PNG/PDF files under {target}")
    return files


def _image_meta(path: Path) -> dict[str, str]:
    info: dict[str, str] = {}
    with Image.open(path) as img:
        if getattr(img, "format", None):
            info["format"] = str(img.format)
        info["size"] = f"{img.width}x{img.height}"
        exif = img.getexif()
        if exif:
            for tag, value in exif.items():
                info[f"exif:{tag}"] = str(value)[:120]
        for key, value in img.info.items():
            if key.lower() in {"exif", "icc_profile"}:
                info[key] = f"<{len(value) if isinstance(value, (bytes, bytearray)) else '?'} bytes>"
            else:
                info[str(key)] = str(value)[:120]
    return info


def _pdf_meta(path: Path) -> dict[str, str]:
    info: dict[str, str] = {}
    reader = PdfReader(str(path))
    meta = reader.metadata
    if meta:
        for key in meta.keys():
            info[str(key)] = str(meta[key])[:120]
    root = reader.trailer.get("/Root") if reader.trailer else None
    if root and "/Metadata" in root:
        info["XMP"] = "present"
    info["pages"] = str(len(reader.pages))
    return info


def read_meta(path: Path) -> dict[str, str]:
    suffix = path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return _image_meta(path)
    if suffix in PDF_SUFFIXES:
        return _pdf_meta(path)
    return {}


def _compare_table(path: Path, before: dict[str, str], after: dict[str, str]) -> Table:
    table = Table(title=str(path.name), show_lines=False)
    table.add_column("Field")
    table.add_column("Before")
    table.add_column("After")
    keys = sorted(set(before) | set(after))
    if not keys:
        table.add_row("—", "(no metadata)", "(no metadata)")
        return table
    for key in keys:
        table.add_row(key, before.get(key, "—"), after.get(key, "—"))
    return table


def scrub_image(src: Path, dest: Path) -> None:
    with Image.open(src) as img:
        fmt = (img.format or src.suffix.lstrip(".")).upper()
        img = ImageOps.exif_transpose(img) or img
        clean = Image.frombytes(img.mode, img.size, img.tobytes())
        save_kw: dict[str, Any] = {}
        if fmt in {"JPEG", "JPG"}:
            if clean.mode not in {"RGB", "L"}:
                clean = clean.convert("RGB")
            save_kw["format"] = "JPEG"
            save_kw["quality"] = 95
            save_kw["exif"] = b""
        elif fmt == "PNG":
            save_kw["format"] = "PNG"
            save_kw["pnginfo"] = None
        else:
            save_kw["format"] = fmt
        dest.parent.mkdir(parents=True, exist_ok=True)
        clean.save(dest, **save_kw)


def scrub_pdf(src: Path, dest: Path) -> None:
    reader = PdfReader(str(src))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.metadata = None
    writer.xmp_metadata = None
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = BytesIO()
    writer.write(tmp)
    dest.write_bytes(tmp.getvalue())


def scrub_file(src: Path, dest: Path) -> None:
    suffix = src.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        scrub_image(src, dest)
    elif suffix in PDF_SUFFIXES:
        scrub_pdf(src, dest)
    else:
        raise ValueError(f"Unsupported: {src}")


def run(console: Console, config: dict[str, Any], dry_run: bool) -> None:
    info(
        console,
        "Strips EXIF (JPEG/PNG) and document info/XMP (PDF).\n"
        "By default writes cleaned copies so originals stay intact.",
    )
    default = str(config.get("default_scrub_dir") or "")
    raw = ask_path(console, "File or folder to scrub", default)
    if not raw:
        warn(console, "No path given.")
        return
    target = assert_user_path(Path(raw))
    if not target.exists():
        raise FileNotFoundError(f"Not found: {target}")

    files = _collect(target)
    total = sum(p.stat().st_size for p in files)
    console.print(f"Found [bold]{len(files)}[/] file(s) ({format_size(total)}).")

    overwrite = ask_yes_no(console, "Overwrite originals instead of writing copies?", default=False)
    output_dir = resolve_output_dir(config)

    if overwrite:
        ok = confirm_destructive(
            console,
            "Overwrite these files in place after stripping metadata.",
            files,
            total_bytes=total,
            dry_run=dry_run,
        )
        if not ok:
            return
        dests = files
    else:
        dests = []
        for src in files:
            if target.is_file():
                dests.append(output_dir / f"{src.stem}.scrubbed{src.suffix.lower()}")
            else:
                rel = src.relative_to(target)
                dests.append(output_dir / rel.parent / f"{rel.stem}.scrubbed{rel.suffix.lower()}")
        console.print(f"Cleaned copies will go under [bold]{output_dir}[/]")
        if dry_run:
            for src, dest in zip(files, dests, strict=True):
                console.print(f"  [dim]would scrub[/] {src} -> {dest}")
            warn(console, "Dry-run: no files written.")
            return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Scrubbing", total=len(files))
        for src, dest in zip(files, dests, strict=True):
            try:
                before = read_meta(src)
            except (UnidentifiedImageError, PdfReadError, OSError) as exc:
                error(console, f"Skip {src.name}: {exc}")
                progress.advance(task)
                continue
            if overwrite:
                tmp = dest.with_suffix(dest.suffix + ".tmp")
                scrub_file(src, tmp)
                tmp.replace(dest)
            else:
                scrub_file(src, dest)
            try:
                after = read_meta(dest)
            except OSError:
                after = {"(read-back)": "failed"}
            console.print(_compare_table(src, before, after))
            leftover = [k for k in after if k not in TECHNICAL_KEYS]
            if leftover:
                warn(console, f"{dest.name}: some fields remain: {', '.join(leftover[:8])}")
            else:
                console.print(f"[green]Clean[/] {dest}")
            progress.advance(task)
