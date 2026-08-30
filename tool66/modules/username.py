"""Build public profile URLs for a handle and note which return HTTP 200."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.error import URLError

from ..http import fetch
from ..result import Result
from ..validate import validate_handle

# Public profile URL templates only. A 200 means the URL returned 200, not
# proof that an account exists (some sites use soft 404 pages).
SITES: tuple[tuple[str, str], ...] = (
    ("GitHub", "https://github.com/{handle}"),
    ("GitLab", "https://gitlab.com/{handle}"),
    ("Bitbucket", "https://bitbucket.org/{handle}"),
    ("Codeberg", "https://codeberg.org/{handle}"),
    ("SourceHut", "https://sr.ht/~{handle}"),
    ("Reddit", "https://www.reddit.com/user/{handle}"),
    ("Hacker News", "https://news.ycombinator.com/user?id={handle}"),
    ("Keybase", "https://keybase.io/{handle}"),
    ("Medium", "https://medium.com/@{handle}"),
    ("Dev.to", "https://dev.to/{handle}"),
    ("HackerOne", "https://hackerone.com/{handle}"),
    ("PyPI", "https://pypi.org/user/{handle}/"),
    ("npm", "https://www.npmjs.com/~{handle}"),
    ("Docker Hub", "https://hub.docker.com/u/{handle}"),
    ("Wikipedia", "https://en.wikipedia.org/wiki/User:{handle}"),
    ("Internet Archive", "https://archive.org/details/@{handle}"),
    ("Twitch", "https://www.twitch.tv/{handle}"),
    ("YouTube", "https://www.youtube.com/@{handle}"),
    ("Linktree", "https://linktr.ee/{handle}"),
)


def profile_url(site: str, handle: str) -> str:
    for name, template in SITES:
        if name.lower() == site.lower():
            return template.format(handle=handle)
    raise ValueError(f"unknown site: {site}")


def _check(url: str, timeout: float) -> dict[str, Any]:
    try:
        response = fetch(url, timeout, max_bytes=2048)
        return {
            "url": url,
            "final_url": response.final_url,
            "status": response.status,
            "ok_http": response.status == 200,
            "error": None,
        }
    except URLError as exc:
        return {
            "url": url,
            "final_url": url,
            "status": None,
            "ok_http": False,
            "error": str(exc.reason if getattr(exc, "reason", None) else exc),
        }


def lookup(handle: str, timeout: float, workers: int = 6) -> Result:
    name = validate_handle(handle)
    planned = [
        {"site": site, "url": template.format(handle=name)}
        for site, template in SITES
    ]
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {
            pool.submit(_check, item["url"], timeout): item for item in planned
        }
        for future in as_completed(futures):
            item = futures[future]
            row = future.result()
            row["site"] = item["site"]
            results.append(row)
    results.sort(key=lambda row: str(row["site"]).lower())
    hits = [row for row in results if row.get("ok_http")]
    return Result(
        module="username",
        source="public profile URLs (operator-supplied handle)",
        target=name,
        ok=True,
        data={
            "handle": name,
            "checked": len(results),
            "http_200": len(hits),
            "note": "HTTP 200 means the public URL returned 200, not a confirmed account.",
            "profiles": results,
        },
    )


def format_text(data: dict[str, Any]) -> str:
    lines = [
        f"handle   {data.get('handle', '')}",
        f"checked  {data.get('checked', 0)}",
        f"http_200 {data.get('http_200', 0)}",
        f"note     {data.get('note', '')}",
        "",
        f"{'STATUS':<8}{'SITE':<18}URL",
    ]
    for row in data.get("profiles") or []:
        status = row.get("status")
        status_text = str(status) if status is not None else "error"
        lines.append(f"{status_text:<8}{row.get('site', ''):<18}{row.get('url', '')}")
    return "\n".join(lines)
