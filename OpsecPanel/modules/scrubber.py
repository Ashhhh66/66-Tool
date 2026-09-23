"""Strip EXIF and document metadata from JPEG, PNG, PDF, and MP4/MOV files you own."""

from __future__ import annotations

import shutil
import struct
from io import BytesIO
from pathlib import Path
from typing import Any

from mutagen import MutagenError
from mutagen.mp4 import MP4
from PIL import Image, ImageOps, UnidentifiedImageError
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError
from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

from safety import assert_user_path, format_size
from ui import ask_path, ask_yes_no, confirm_destructive, error, info, warn

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
PDF_SUFFIXES = {".pdf"}
VIDEO_SUFFIXES = {".mp4", ".m4v", ".mov"}
SUPPORTED = IMAGE_SUFFIXES | PDF_SUFFIXES | VIDEO_SUFFIXES
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
    "duration",
    "bitrate",
    "codec",
    "channels",
    "sample_rate",
}

# C2PA Manifest Store and XMP UUIDs used in ISO-BMFF / QuickTime.
_C2PA_UUID = bytes.fromhex("D8FEC3D61B0E483C98BE202ED6269A09")
_XMP_UUID = bytes.fromhex("BE7ACFCB97A942E89C71999991E32340")
_DROP_TYPES = {b"udta", b"meta", b"xml ", b"XMP_"}
_CONTAINERS = {b"moov", b"trak", b"mdia", b"minf", b"stbl", b"edts", b"moof", b"traf"}


def _collect(target: Path) -> list[Path]:
    if target.is_file():
        if target.suffix.lower() not in SUPPORTED:
            raise ValueError(f"Unsupported type: {target.suffix} (use JPEG, PNG, PDF, MP4, or MOV)")
        return [target]
    files = sorted(
        p for p in target.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED
    )
    if not files:
        raise FileNotFoundError(f"No JPEG/PNG/PDF/MP4/MOV files under {target}")
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


def _mp4_meta(path: Path) -> dict[str, str]:
    info: dict[str, str] = {"format": path.suffix.lower().lstrip(".").upper()}
    raw = path.read_bytes()
    if _C2PA_UUID in raw or b"c2pa" in raw:
        info["c2pa"] = "present"
    if _XMP_UUID in raw or b"<?xpacket" in raw:
        info["xmp"] = "present"
    try:
        video = MP4(str(path))
    except MutagenError:
        return info
    stream = video.info
    if stream is not None:
        length = getattr(stream, "length", None)
        if length:
            info["duration"] = f"{float(length):.1f}s"
        bitrate = getattr(stream, "bitrate", None)
        if bitrate:
            info["bitrate"] = str(bitrate)
        codec = getattr(stream, "codec", None)
        if codec:
            info["codec"] = str(codec)
    for key, value in (video.tags or {}).items():
        rendered = str(value)
        if key == "covr" or "cover" in str(key).lower():
            rendered = f"<{len(value) if isinstance(value, list) else 1} item(s)>"
        info[str(key)] = rendered[:120]
    return info


def read_meta(path: Path) -> dict[str, str]:
    suffix = path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return _image_meta(path)
    if suffix in PDF_SUFFIXES:
        return _pdf_meta(path)
    if suffix in VIDEO_SUFFIXES:
        return _mp4_meta(path)
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


def _iter_boxes(data: bytes, start: int, end: int):
    pos = start
    while pos + 8 <= end:
        size, typ = struct.unpack(">I4s", data[pos : pos + 8])
        if size == 1:
            if pos + 16 > end:
                break
            size64 = struct.unpack(">Q", data[pos + 8 : pos + 16])[0]
            box_end = pos + size64
            hdr = 16
        elif size == 0:
            box_end = end
            hdr = 8
        else:
            box_end = pos + size
            hdr = 8
        if box_end > end or box_end <= pos:
            break
        yield pos, hdr, typ, box_end
        pos = box_end


def _drop_box(typ: bytes, payload: bytes) -> bool:
    if typ in _DROP_TYPES:
        return True
    if typ == b"uuid" and len(payload) >= 16 and payload[:16] in {_C2PA_UUID, _XMP_UUID}:
        return True
    if typ == b"uuid" and (b"c2pa" in payload[:64] or b"C2PA" in payload[:64]):
        return True
    return False


def _blank_boxes(buf: bytearray, start: int, end: int) -> None:
    """Turn metadata boxes into same-size 'free' space so mdat offsets stay valid."""
    snapshot = bytes(buf[start:end])
    for pos, hdr, typ, box_end in _iter_boxes(snapshot, 0, len(snapshot)):
        abs_pos = start + pos
        abs_end = start + box_end
        payload = bytes(buf[abs_pos + hdr : abs_end])
        if _drop_box(typ, payload):
            buf[abs_pos + 4 : abs_pos + 8] = b"free"
            buf[abs_pos + hdr : abs_end] = b"\x00" * (abs_end - abs_pos - hdr)
            continue
        if typ in _CONTAINERS:
            _blank_boxes(buf, abs_pos + hdr, abs_end)


def _strip_mp4_boxes(path: Path) -> None:
    data = bytearray(path.read_bytes())
    if len(data) < 16 or b"ftyp" not in data[:32]:
        return
    _blank_boxes(data, 0, len(data))
    path.write_bytes(data)


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


def scrub_mp4(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.resolve() != dest.resolve():
        shutil.copyfile(src, dest)
    try:
        video = MP4(str(dest))
        video.delete()
    except MutagenError:
        pass
    _strip_mp4_boxes(dest)


def scrub_file(src: Path, dest: Path) -> None:
    suffix = src.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        scrub_image(src, dest)
    elif suffix in PDF_SUFFIXES:
        scrub_pdf(src, dest)
    elif suffix in VIDEO_SUFFIXES:
        scrub_mp4(src, dest)
    else:
        raise ValueError(f"Unsupported: {src}")


def run(console: Console, config: dict[str, Any], dry_run: bool) -> None:
    _ = config
    info(
        console,
        "Strips EXIF (JPEG/PNG), PDF info/XMP, and MP4/MOV tags, GPS, XMP, C2PA boxes.\n"
        "Video/audio is copied, not re-encoded. Writes *.scrubbed.* next to the original.\n\n"
        "Instagram “AI content” is often from the pixels or Meta’s detector, not file tags.\n"
        "This cannot remove invisible watermarks or stop Instagram classifying a clip as AI.",
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
        dests = [src.with_name(f"{src.stem}.scrubbed{src.suffix.lower()}") for src in files]
        console.print("[dim]Cleaned copies are written next to each original as *.scrubbed.*[/]")
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
            except (UnidentifiedImageError, PdfReadError, MutagenError, OSError) as exc:
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
            console.print(f"[bold]Saved:[/] {dest.resolve()}")
            if dest.suffix.lower() in VIDEO_SUFFIXES:
                console.print(
                    "[dim]Upload this .scrubbed file, not the original. "
                    "If Instagram still says AI, that is their detector, not leftover tags.[/]"
                )
            progress.advance(task)
