"""Read the public TLS certificate a host presents."""

from __future__ import annotations

import os
import socket
import ssl
import tempfile
from datetime import datetime
from typing import Any

from .. import dnsproto
from ..result import Result
from ..validate import validate_host

ISO_TRY = ("%b %d %H:%M:%S %Y %Z", "%Y%m%d%H%M%SZ")


def _connect(hostname: str, port: int, timeout: float) -> socket.socket:
    try:
        return socket.create_connection((hostname, port), timeout=timeout)
    except socket.gaierror:
        parsed = dnsproto.query_udp(hostname, "A", timeout)
        answers = parsed.get("answers") or []
        if isinstance(answers, list):
            for answer in answers:
                if isinstance(answer, dict) and answer.get("type") == "A" and answer.get("data"):
                    return socket.create_connection((str(answer["data"]), port), timeout=timeout)
        raise


def _pairs_to_dict(entries: object) -> dict[str, str]:
    out: dict[str, str] = {}
    if not entries:
        return out
    for item in entries:
        if isinstance(item, tuple) and item and isinstance(item[0], tuple):
            for key, value in item:
                out[str(key)] = str(value)
        elif isinstance(item, tuple) and len(item) == 2:
            out[str(item[0])] = str(item[1])
    return out


def _decode_der(der: bytes) -> dict[str, Any]:
    pem = ssl.DER_cert_to_PEM_cert(der)
    decode = getattr(getattr(ssl, "_ssl", None), "_test_decode_cert", None)
    if decode is None:
        return {"pem": pem}
    handle = tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False, encoding="utf-8")
    try:
        handle.write(pem)
        handle.close()
        parsed = decode(handle.name)
    finally:
        try:
            os.unlink(handle.name)
        except OSError:
            pass
    if isinstance(parsed, dict):
        parsed = dict(parsed)
        parsed["pem"] = pem
        return parsed
    return {"pem": pem}


def _iso(value: str) -> str:
    text = value.strip()
    for fmt in ISO_TRY:
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.isoformat() + "Z"
        except ValueError:
            continue
    return text


def lookup(host: str, timeout: float, port: int | None = None) -> Result:
    hostname, parsed_port = validate_host(host)
    dest_port = port or parsed_port or 443
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    try:
        sock = _connect(hostname, dest_port, timeout)
        with context.wrap_socket(sock, server_hostname=hostname) as tls:
            der = tls.getpeercert(binary_form=True)
            proto = tls.version()
    except OSError as exc:
        return Result(
            module="cert",
            source=f"TLS handshake {hostname}:{dest_port}",
            target=f"{hostname}:{dest_port}",
            ok=False,
            error=str(exc),
        )
    if not der:
        return Result(
            module="cert",
            source=f"TLS handshake {hostname}:{dest_port}",
            target=f"{hostname}:{dest_port}",
            ok=False,
            error="peer presented no certificate",
        )
    parsed = _decode_der(der)
    sans = parsed.get("subjectAltName") or ()
    san_values = [value for kind, value in sans if kind == "DNS"] if sans else []
    subject = _pairs_to_dict(parsed.get("subject"))
    issuer = _pairs_to_dict(parsed.get("issuer"))
    not_before = str(parsed.get("notBefore") or "")
    not_after = str(parsed.get("notAfter") or "")
    return Result(
        module="cert",
        source=f"TLS certificate presented by {hostname}:{dest_port}",
        target=f"{hostname}:{dest_port}",
        ok=True,
        data={
            "host": hostname,
            "port": dest_port,
            "protocol": proto,
            "subject": subject,
            "issuer": issuer,
            "not_before": not_before,
            "not_after": not_after,
            "not_before_iso": _iso(not_before) if not_before else "",
            "not_after_iso": _iso(not_after) if not_after else "",
            "serial": parsed.get("serialNumber"),
            "sans": san_values,
        },
    )


def format_text(data: dict[str, Any]) -> str:
    issuer = data.get("issuer") or {}
    subject = data.get("subject") or {}
    lines = [
        f"host     {data.get('host', '')}:{data.get('port', '')}",
        f"proto    {data.get('protocol', '')}",
        f"subject  {subject.get('commonName', subject)}",
        f"issuer   {issuer.get('commonName', issuer)}",
        f"from     {data.get('not_before', '')}",
        f"until    {data.get('not_after', '')}",
    ]
    sans = data.get("sans") or []
    if sans:
        lines.append("sans     " + ", ".join(sans))
    return "\n".join(lines)
