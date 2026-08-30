"""Path and identifier guards: current user only, no batch lookups."""

from __future__ import annotations

import os
import re
import ssl
import urllib.error
import urllib.request
from pathlib import Path

USER_AGENT = "66-Tool (personal privacy hygiene tool)"

_WINDOWS_SYSTEM = (
    Path(os.environ.get("WINDIR", r"C:\Windows")),
    Path(os.environ.get("SystemRoot", r"C:\Windows")),
    Path(r"C:\Program Files"),
    Path(r"C:\Program Files (x86)"),
    Path(r"C:\ProgramData"),
    Path(r"C:\$Recycle.Bin"),
)


def format_size(num: int) -> str:
    units = ("B", "KB", "MB", "GB", "TB")
    size = float(max(0, num))
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{num} B"


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except (ValueError, OSError):
        return False


def _forbidden_roots() -> list[Path]:
    roots: list[Path] = []
    for item in _WINDOWS_SYSTEM:
        try:
            roots.append(item.resolve())
        except OSError:
            roots.append(item)
    linux = [Path("/etc"), Path("/usr"), Path("/bin"), Path("/sbin"), Path("/boot"), Path("/root")]
    if os.name != "nt":
        roots.extend(linux)
    return roots


def assert_user_path(path: Path, *, allow_cwd: bool = True) -> Path:
    """Resolve *path* and refuse system dirs and other users' profiles."""
    try:
        resolved = path.expanduser().resolve()
    except OSError as exc:
        raise PermissionError(f"Cannot resolve path: {path}") from exc

    home = Path.home().resolve()
    cwd = Path.cwd().resolve()

    for root in _forbidden_roots():
        if resolved == root or _is_relative_to(resolved, root):
            raise PermissionError(f"Refusing system path: {resolved}")

    if os.name == "nt":
        users = home.parent
        if _is_relative_to(resolved, users) and not _is_relative_to(resolved, home) and resolved != home:
            raise PermissionError("Refusing a path under another user's profile.")
    else:
        if resolved.parts[:2] == ("/", "home") and not _is_relative_to(resolved, home) and resolved != home:
            raise PermissionError("Refusing a path under another user's home.")

    if _is_relative_to(resolved, home) or resolved == home:
        return resolved
    if allow_cwd and (_is_relative_to(resolved, cwd) or resolved == cwd):
        return resolved

    raise PermissionError(
        "Path is outside your home directory and the current working directory."
    )


def validate_own_identifier(value: str) -> str:
    """Accept a single email or username the operator typed for themselves."""
    raw = (value or "").strip()
    if not raw:
        raise ValueError("Enter a single email address or username.")
    if any(ch in raw for ch in ",;\n\r\t|"):
        raise ValueError("Only one identifier is allowed — no lists.")
    if raw.count("@") > 1:
        raise ValueError("Only one email address is allowed.")
    lowered = raw.lower()
    if lowered.startswith(("file:", "http://", "https://")):
        raise ValueError("Enter an email or username, not a URL or file.")
    if "/" in raw or "\\" in raw:
        raise ValueError("File paths are not accepted. Type one identifier.")
    if len(raw) >= 2 and raw[1] == ":":
        raise ValueError("File paths are not accepted. Type one identifier.")
    if Path(raw).suffix.lower() in {".txt", ".csv", ".json", ".lst"}:
        raise ValueError("Looks like a list file. Type one email or username.")
    if " " in raw:
        raise ValueError("Only one identifier is allowed (no spaces / lists).")
    if not re.fullmatch(r"[A-Za-z0-9._%+\-@]{1,254}", raw):
        raise ValueError("Identifier contains characters that are not allowed.")
    return raw


def validate_single_url(value: str) -> str:
    """Accept one http(s) URL the operator chose to inspect."""
    raw = (value or "").strip().strip('"').strip("'")
    if not raw:
        raise ValueError("Paste a single http:// or https:// URL.")
    if any(ch in raw for ch in ",\n\r\t"):
        raise ValueError("Only one URL is allowed — no lists.")
    if " " in raw:
        raise ValueError("Only one URL is allowed (no spaces / lists).")
    lowered = raw.lower()
    if lowered.startswith(("javascript:", "data:", "file:", "ftp:")):
        raise ValueError("Only http:// or https:// URLs can be inspected.")
    if not lowered.startswith(("http://", "https://")):
        raise ValueError("URL must start with http:// or https://")
    if raw.count("://") > 1:
        raise ValueError("Only one URL is allowed.")
    return raw


def http_get(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 12.0,
) -> tuple[int, bytes, str]:
    """HTTPS GET for this tool's self-checks. Returns status, body, final URL."""
    req = urllib.request.Request(url, method="GET")
    merged = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if headers:
        merged.update(headers)
    for key, val in merged.items():
        req.add_header(key, val)
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return int(resp.getcode() or 0), resp.read(), resp.geturl()
    except urllib.error.HTTPError as exc:
        body = exc.read() if exc.fp else b""
        return int(exc.code), body, url
