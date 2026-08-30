"""Minimal DNS/UDP query and response parser (IN class only)."""

from __future__ import annotations

import random
import socket
import struct
from typing import Iterable

QTYPES = {
    "A": 1,
    "NS": 2,
    "CNAME": 5,
    "MX": 15,
    "TXT": 16,
    "AAAA": 28,
}
TYPE_NAMES = {code: name for name, code in QTYPES.items()}
CLASS_IN = 1
RCODE_NAMES = {
    0: "NOERROR",
    1: "FORMERR",
    2: "SERVFAIL",
    3: "NXDOMAIN",
    4: "NOTIMP",
    5: "REFUSED",
}


def encode_name(name: str) -> bytes:
    labels = name.rstrip(".").split(".") if name.rstrip(".") else []
    out = bytearray()
    for label in labels:
        raw = label.encode("idna")
        if not raw or len(raw) > 63:
            raise ValueError(f"invalid DNS label: {label}")
        out.append(len(raw))
        out.extend(raw)
    out.append(0)
    return bytes(out)


def decode_name(message: bytes, offset: int, depth: int = 0) -> tuple[str, int]:
    if depth > 10:
        raise ValueError("DNS name compression loop")
    labels: list[str] = []
    jumped = False
    end = offset
    while True:
        if offset >= len(message):
            raise ValueError("truncated DNS name")
        length = message[offset]
        if length == 0:
            if not jumped:
                end = offset + 1
            break
        if length & 0xC0 == 0xC0:
            if offset + 1 >= len(message):
                raise ValueError("truncated DNS pointer")
            pointer = ((length & 0x3F) << 8) | message[offset + 1]
            if not jumped:
                end = offset + 2
                jumped = True
            suffix, _ = decode_name(message, pointer, depth + 1)
            labels.append(suffix)
            break
        if length & 0xC0:
            raise ValueError("unsupported DNS name encoding")
        offset += 1
        label = message[offset : offset + length]
        if len(label) != length:
            raise ValueError("truncated DNS label")
        try:
            labels.append(label.decode("idna"))
        except UnicodeError:
            labels.append(label.decode("ascii", errors="replace"))
        offset += length
        if not jumped:
            end = offset
    joined = ".".join(part for part in labels if part)
    return (joined if joined else "."), end


def build_query(name: str, qtype: str, ident: int | None = None) -> bytes:
    if qtype not in QTYPES:
        raise ValueError(f"unsupported record type: {qtype}")
    header_id = ident if ident is not None else random.randint(0, 65535)
    header = struct.pack("!HHHHHH", header_id, 0x0100, 1, 0, 0, 0)
    question = encode_name(name) + struct.pack("!HH", QTYPES[qtype], CLASS_IN)
    return header + question


def _read_rdata(qtype: int, rdata: bytes, message: bytes, rdata_offset: int) -> str:
    if qtype == QTYPES["A"] and len(rdata) == 4:
        return socket.inet_ntop(socket.AF_INET, rdata)
    if qtype == QTYPES["AAAA"] and len(rdata) == 16:
        return socket.inet_ntop(socket.AF_INET6, rdata)
    if qtype in (QTYPES["NS"], QTYPES["CNAME"]):
        name, _ = decode_name(message, rdata_offset)
        return name
    if qtype == QTYPES["MX"] and len(rdata) >= 3:
        preference = struct.unpack("!H", rdata[:2])[0]
        name, _ = decode_name(message, rdata_offset + 2)
        return f"{preference} {name}"
    if qtype == QTYPES["TXT"]:
        chunks: list[str] = []
        cursor = 0
        while cursor < len(rdata):
            size = rdata[cursor]
            cursor += 1
            chunks.append(rdata[cursor : cursor + size].decode("utf-8", errors="replace"))
            cursor += size
        return "".join(chunks)
    return rdata.hex()


def parse_message(message: bytes) -> dict[str, object]:
    if len(message) < 12:
        raise ValueError("truncated DNS header")
    ident, flags, qdcount, ancount, nscount, arcount = struct.unpack(
        "!HHHHHH", message[:12]
    )
    offset = 12
    questions: list[dict[str, object]] = []
    for _ in range(qdcount):
        name, offset = decode_name(message, offset)
        if offset + 4 > len(message):
            raise ValueError("truncated DNS question")
        qtype, qclass = struct.unpack("!HH", message[offset : offset + 4])
        offset += 4
        questions.append({"name": name, "type": TYPE_NAMES.get(qtype, str(qtype))})
        del qclass
    answers: list[dict[str, object]] = []
    for _ in range(ancount):
        name, offset = decode_name(message, offset)
        if offset + 10 > len(message):
            raise ValueError("truncated DNS record")
        rtype, rclass, ttl, rdlength = struct.unpack("!HHIH", message[offset : offset + 10])
        offset += 10
        rdata = message[offset : offset + rdlength]
        if len(rdata) != rdlength:
            raise ValueError("truncated DNS rdata")
        answers.append(
            {
                "name": name,
                "type": TYPE_NAMES.get(rtype, str(rtype)),
                "ttl": ttl,
                "data": _read_rdata(rtype, rdata, message, offset),
            }
        )
        offset += rdlength
        del rclass
    return {
        "id": ident,
        "rcode": flags & 0x000F,
        "rcode_name": RCODE_NAMES.get(flags & 0x000F, str(flags & 0x000F)),
        "truncated": bool(flags & 0x0200),
        "questions": questions,
        "answers": answers,
        "authority_count": nscount,
        "additional_count": arcount,
    }


def query_udp(
    name: str,
    qtype: str,
    timeout: float,
    resolvers: Iterable[str] = ("1.1.1.1", "8.8.8.8"),
) -> dict[str, object]:
    payload = build_query(name, qtype)
    last_error: Exception | None = None
    for resolver in resolvers:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        try:
            sock.sendto(payload, (resolver, 53))
            data, _ = sock.recvfrom(4096)
            parsed = parse_message(data)
            parsed["resolver"] = resolver
            return parsed
        except OSError as exc:
            last_error = exc
        finally:
            sock.close()
    raise OSError(str(last_error) if last_error else "DNS query failed")
