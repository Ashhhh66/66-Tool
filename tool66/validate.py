"""Input checks for public-source lookups."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.(?!-)[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
)
HANDLE_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
EMAIL_RE = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
)


def normalize_domain(value: str) -> str:
    text = value.strip().lower()
    if "://" in text:
        parsed = urlparse(text)
        text = parsed.hostname or ""
    text = text.split("/")[0].split("?")[0].rstrip(".")
    if text.startswith("*."):
        text = text[2:]
    if not text or not DOMAIN_RE.match(text):
        raise ValueError(f"invalid domain: {value}")
    return text


def validate_handle(value: str) -> str:
    text = value.strip()
    if text.startswith("@"):
        text = text[1:]
    if not HANDLE_RE.match(text):
        raise ValueError(f"invalid handle: {value}")
    return text


def validate_email(value: str) -> str:
    text = value.strip()
    if not EMAIL_RE.match(text):
        raise ValueError(f"invalid email: {value}")
    local, _, domain = text.rpartition("@")
    if not local or not domain or ".." in text:
        raise ValueError(f"invalid email: {value}")
    return text


def validate_public_url(value: str) -> str:
    text = value.strip()
    parsed = urlparse(text)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("only http and https urls are allowed")
    if parsed.username or parsed.password:
        raise ValueError("url must not include credentials")
    if not parsed.hostname:
        raise ValueError(f"invalid url: {value}")
    return text


def validate_host(value: str) -> tuple[str, int | None]:
    text = value.strip()
    if "://" in text:
        parsed = urlparse(text)
        if parsed.username or parsed.password:
            raise ValueError("host must not include credentials")
        host = parsed.hostname or ""
        port = parsed.port
        if not host:
            raise ValueError(f"invalid host: {value}")
        return host, port
    if text.startswith("["):
        end = text.find("]")
        if end == -1:
            raise ValueError(f"invalid host: {value}")
        host = text[1:end]
        rest = text[end + 1 :]
        port = int(rest[1:]) if rest.startswith(":") and rest[1:] else None
        ipaddress.ip_address(host)
        return host, port
    if text.count(":") == 1:
        host, port_text = text.rsplit(":", 1)
        return host, int(port_text)
    return text, None


def parse_ip(value: str) -> str:
    return str(ipaddress.ip_address(value.strip()))
