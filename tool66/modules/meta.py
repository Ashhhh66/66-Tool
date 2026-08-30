"""Read metadata from a local file the operator provides."""

from __future__ import annotations

import hashlib
import struct
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..result import Result

EXIF_TAGS = {
    0x010F: "make",
    0x0110: "model",
    0x0112: "orientation",
    0x0131: "software",
    0x0132: "datetime",
    0x010E: "image_description",
    0x013B: "artist",
    0x8298: "copyright",
    0x8769: "exif_ifd",
    0x8825: "gps_ifd",
}
EXIF_SUBTAGS = {
    0x9003: "datetime_original",
    0x9004: "datetime_digitized",
}
GPS_TAGS = {
    1: "lat_ref",
    2: "lat",
    3: "lon_ref",
    4: "lon",
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _unpack(fmt: str, data: bytes, offset: int):
    size = struct.calcsize(fmt)
    return struct.unpack(fmt, data[offset : offset + size])


def _read_value(data: bytes, offset: int, typ: int, count: int, endian: str) -> Any:
    type_size = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1}.get(typ)
    if type_size is None:
        return None
    byte_count = type_size * count
    if byte_count <= 4:
        raw = data[offset : offset + byte_count]
    else:
        (ptr,) = _unpack(endian + "I", data, offset)
        raw = data[ptr : ptr + byte_count]
    if typ == 2:
        return raw.split(b"\x00", 1)[0].decode("utf-8", errors="replace")
    if typ == 3:
        values = struct.unpack(endian + ("H" * count), raw[: 2 * count])
        return values[0] if count == 1 else list(values)
    if typ == 4:
        values = struct.unpack(endian + ("I" * count), raw[: 4 * count])
        return values[0] if count == 1 else list(values)
    if typ == 5:
        nums = []
        for index in range(count):
            num, den = struct.unpack(endian + "II", raw[index * 8 : index * 8 + 8])
            nums.append((num, den))
        return nums[0] if count == 1 else nums
    if typ in (1, 7):
        return raw
    return None


def _read_ifd(data: bytes, ifd_offset: int, endian: str, tags: dict[int, str]) -> dict[str, Any]:
    if ifd_offset + 2 > len(data):
        return {}
    (count,) = _unpack(endian + "H", data, ifd_offset)
    out: dict[str, Any] = {}
    cursor = ifd_offset + 2
    for _ in range(count):
        if cursor + 12 > len(data):
            break
        tag, typ, tag_count = _unpack(endian + "HHI", data, cursor)
        value = _read_value(data, cursor + 8, typ, tag_count, endian)
        name = tags.get(tag)
        if name and value is not None:
            out[name] = value
        cursor += 12
    return out


def parse_jpeg_exif(data: bytes) -> dict[str, Any]:
    if data[:2] != b"\xff\xd8":
        return {}
    offset = 2
    while offset + 4 <= len(data):
        if data[offset] != 0xFF:
            break
        marker = data[offset + 1]
        if marker == 0xDA:
            break
        length = struct.unpack(">H", data[offset + 2 : offset + 4])[0]
        payload = data[offset + 4 : offset + 2 + length]
        if marker == 0xE1 and payload.startswith(b"Exif\x00\x00"):
            return _parse_tiff_exif(payload[6:])
        offset += 2 + length
    return {}


def _rational_to_deg(value: object) -> float | None:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return None
    total = 0.0
    div = 1.0
    for item in value:
        if not isinstance(item, (list, tuple)) or len(item) != 2 or not item[1]:
            return None
        total += (item[0] / item[1]) / div
        div *= 60.0
    return total


def _parse_tiff_exif(data: bytes) -> dict[str, Any]:
    if data[:2] == b"II":
        endian = "<"
    elif data[:2] == b"MM":
        endian = ">"
    else:
        return {}
    (magic,) = _unpack(endian + "H", data, 2)
    if magic != 42:
        return {}
    (ifd0,) = _unpack(endian + "I", data, 4)
    fields = _read_ifd(data, ifd0, endian, EXIF_TAGS)
    if "exif_ifd" in fields and isinstance(fields["exif_ifd"], int):
        fields.update(_read_ifd(data, fields.pop("exif_ifd"), endian, EXIF_SUBTAGS))
    if "gps_ifd" in fields and isinstance(fields["gps_ifd"], int):
        gps = _read_ifd(data, fields.pop("gps_ifd"), endian, GPS_TAGS)
        lat = _rational_to_deg(gps.get("lat"))
        lon = _rational_to_deg(gps.get("lon"))
        if lat is not None and str(gps.get("lat_ref", "")).upper().startswith("S"):
            lat = -lat
        if lon is not None and str(gps.get("lon_ref", "")).upper().startswith("W"):
            lon = -lon
        if lat is not None and lon is not None:
            fields["gps"] = {"lat": lat, "lon": lon}
    return fields


def parse_png_text(data: bytes) -> dict[str, str]:
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return {}
    out: dict[str, str] = {}
    offset = 8
    while offset + 8 <= len(data):
        (length,) = struct.unpack(">I", data[offset : offset + 4])
        name = data[offset + 4 : offset + 8]
        chunk = data[offset + 8 : offset + 8 + length]
        if name == b"IEND":
            break
        if name == b"tEXt" and b"\x00" in chunk:
            key, value = chunk.split(b"\x00", 1)
            out[key.decode("latin-1", errors="replace")] = value.decode(
                "latin-1", errors="replace"
            )
        elif name == b"zTXt" and b"\x00" in chunk:
            key, rest = chunk.split(b"\x00", 1)
            if rest and rest[0] == 0:
                try:
                    text = zlib.decompress(rest[1:]).decode("latin-1", errors="replace")
                    out[key.decode("latin-1", errors="replace")] = text
                except zlib.error:
                    pass
        offset += 12 + length
    return out


def parse_pdf_info(data: bytes) -> dict[str, str]:
    if not data.startswith(b"%PDF"):
        return {}
    text = data[:80_000].decode("latin-1", errors="replace")
    out: dict[str, str] = {}
    for key in ("Title", "Author", "Subject", "Creator", "Producer", "CreationDate", "ModDate"):
        token = f"/{key}"
        start = text.find(token)
        if start == -1:
            continue
        chunk = text[start + len(token) : start + len(token) + 200].strip()
        if chunk.startswith("("):
            end = chunk.find(")", 1)
            if end != -1:
                out[key.lower()] = chunk[1:end]
    return out


def lookup(path_text: str) -> Result:
    path = Path(path_text)
    if path.is_dir():
        return Result(
            module="meta",
            source="local file metadata (operator-provided)",
            target=str(path),
            ok=False,
            error="path is a directory",
        )
    if not path.is_file():
        return Result(
            module="meta",
            source="local file metadata (operator-provided)",
            target=str(path),
            ok=False,
            error="file not found",
        )
    data = path.read_bytes()
    magic = data[:12]
    kind = "unknown"
    metadata: dict[str, Any] = {}
    if data[:2] == b"\xff\xd8":
        kind = "jpeg"
        metadata = parse_jpeg_exif(data)
    elif data[:8] == b"\x89PNG\r\n\x1a\n":
        kind = "png"
        metadata = parse_png_text(data)
    elif data.startswith(b"%PDF"):
        kind = "pdf"
        metadata = parse_pdf_info(data)
    stat = path.stat()
    return Result(
        module="meta",
        source="local file metadata (operator-provided)",
        target=str(path),
        ok=True,
        data={
            "path": str(path.resolve()),
            "size": stat.st_size,
            "modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            "sha256": hashlib.sha256(data).hexdigest() if stat.st_size <= 32 * 1024 * 1024 else file_sha256(path),
            "kind": kind,
            "magic_hex": magic.hex(),
            "metadata": metadata,
        },
    )


def format_text(data: dict[str, Any]) -> str:
    lines = [
        f"path     {data.get('path', '')}",
        f"kind     {data.get('kind', '')}",
        f"size     {data.get('size', '')}",
        f"sha256   {data.get('sha256', '')}",
        f"mtime    {data.get('modified_utc', '')}",
    ]
    metadata = data.get("metadata") or {}
    if not metadata:
        lines.append("meta     (none parsed)")
        return "\n".join(lines)
    for key, value in metadata.items():
        lines.append(f"{key:<8} {value}")
    return "\n".join(lines)
