"""Polite HTTP GET/HEAD for public URLs only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

USER_AGENT = "Ashh66-66-Tool/1.0 (authorized public-source lookup)"


@dataclass(frozen=True)
class FetchResult:
    url: str
    final_url: str
    status: int
    headers: dict[str, str]
    body: bytes


def fetch(
    url: str,
    timeout: float,
    *,
    method: str = "GET",
    headers: Mapping[str, str] | None = None,
    max_bytes: int = 256_000,
) -> FetchResult:
    """Fetch a public HTTP(S) URL.

    4xx/5xx still return a FetchResult so callers can record the status.
    Transport failures raise URLError.
    """
    request_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "*/*",
    }
    if headers:
        request_headers.update(headers)
    request = Request(url, method=method, headers=request_headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read(max_bytes)
            return FetchResult(
                url=url,
                final_url=response.geturl(),
                status=int(response.status),
                headers={str(key): str(value) for key, value in response.headers.items()},
                body=body,
            )
    except TimeoutError as exc:
        raise URLError(str(exc)) from exc
    except HTTPError as exc:
        body = b""
        try:
            body = exc.read(max_bytes)
        except Exception:
            body = b""
        header_map = {}
        if exc.headers is not None:
            header_map = {str(key): str(value) for key, value in exc.headers.items()}
        return FetchResult(
            url=url,
            final_url=exc.geturl() if hasattr(exc, "geturl") else url,
            status=int(exc.code),
            headers=header_map,
            body=body,
        )
