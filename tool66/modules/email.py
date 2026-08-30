"""Email syntax, Gravatar helpers, and public breach-lookup links only."""

from __future__ import annotations

import hashlib
from typing import Any
from urllib.error import URLError

from ..http import fetch
from ..result import Result
from ..validate import validate_email

# Human pages only. 66-Tool never queries breach databases or HIBP APIs.
BREACH_LOOKUP_PAGES = (
    "https://haveibeenpwned.com/",
    "https://monitor.mozilla.org/",
)


def gravatar_hash(email: str) -> str:
    normalized = email.strip().lower()
    data = normalized.encode("utf-8")
    try:
        return hashlib.md5(data, usedforsecurity=False).hexdigest()
    except TypeError:
        return hashlib.md5(data).hexdigest()


def gravatar_urls(digest: str) -> dict[str, str]:
    return {
        "avatar": f"https://www.gravatar.com/avatar/{digest}?d=404",
        "profile_json": f"https://www.gravatar.com/{digest}.json",
    }


def lookup(address: str, timeout: float) -> Result:
    email = validate_email(address)
    digest = gravatar_hash(email)
    urls = gravatar_urls(digest)
    gravatar_present = None
    gravatar_error = None
    try:
        response = fetch(urls["avatar"], timeout, max_bytes=64)
        gravatar_present = response.status == 200
    except URLError as exc:
        gravatar_error = str(exc.reason if getattr(exc, "reason", None) else exc)
    return Result(
        module="email",
        source="local syntax check + public Gravatar URLs",
        target=email,
        ok=True,
        data={
            "email": email,
            "syntax_ok": True,
            "gravatar_md5": digest,
            "gravatar_urls": urls,
            "gravatar_image_present": gravatar_present,
            "gravatar_error": gravatar_error,
            "breach_lookup_pages": list(BREACH_LOOKUP_PAGES),
            "note": (
                "66-Tool does not query breach databases. Open a lookup "
                "page and paste the address yourself if you are allowed to."
            ),
        },
    )


def format_text(data: dict[str, Any]) -> str:
    present = data.get("gravatar_image_present")
    if present is True:
        gravatar_state = "public image (200)"
    elif present is False:
        gravatar_state = "no custom image (404)"
    else:
        gravatar_state = data.get("gravatar_error") or "not checked"
    lines = [
        f"email    {data.get('email', '')}",
        f"syntax   ok",
        f"ghash    {data.get('gravatar_md5', '')}",
        f"gravatar {gravatar_state}",
        f"avatar   {(data.get('gravatar_urls') or {}).get('avatar', '')}",
        "",
        "breach lookup pages (paste the address yourself):",
    ]
    for url in data.get("breach_lookup_pages") or []:
        lines.append(f"  {url}")
    lines.append("")
    lines.append(str(data.get("note") or ""))
    return "\n".join(lines)
