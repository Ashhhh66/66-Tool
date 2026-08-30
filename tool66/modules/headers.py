"""Fetch public HTTP response headers for a URL."""

from __future__ import annotations

from typing import Any
from urllib.error import URLError

from ..http import fetch
from ..result import Result
from ..validate import validate_public_url


def lookup(url: str, timeout: float) -> Result:
    target = validate_public_url(url)
    try:
        response = fetch(target, timeout, max_bytes=1024)
    except URLError as exc:
        return Result(
            module="headers",
            source="public HTTP(S) response headers",
            target=target,
            ok=False,
            error=str(exc.reason if getattr(exc, "reason", None) else exc),
        )
    return Result(
        module="headers",
        source="public HTTP(S) response headers",
        target=target,
        ok=True,
        data={
            "requested_url": target,
            "final_url": response.final_url,
            "status": response.status,
            "headers": response.headers,
        },
    )


def format_text(data: dict[str, Any]) -> str:
    lines = [
        f"status   {data.get('status', '')}",
        f"final    {data.get('final_url', '')}",
        "",
    ]
    headers = data.get("headers") or {}
    width = max((len(str(key)) for key in headers), default=8)
    for key, value in headers.items():
        lines.append(f"{key:<{width}}  {value}")
    return "\n".join(lines)
