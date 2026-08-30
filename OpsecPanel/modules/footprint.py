"""Public pages that might exist for YOUR handle or email. No other people."""

from __future__ import annotations

import hashlib
import time
from typing import Any

from rich.console import Console
from rich.table import Table

from safety import USER_AGENT, http_get, validate_own_identifier
from ui import error, info, warn

SITES: tuple[tuple[str, str], ...] = (
    ("GitHub", "https://github.com/{handle}"),
    ("GitLab", "https://gitlab.com/{handle}"),
    ("Reddit", "https://www.reddit.com/user/{handle}"),
    ("Hacker News", "https://news.ycombinator.com/user?id={handle}"),
    ("Keybase", "https://keybase.io/{handle}"),
    ("Dev.to", "https://dev.to/{handle}"),
    ("PyPI", "https://pypi.org/user/{handle}/"),
    ("npm", "https://www.npmjs.com/~{handle}"),
    ("Twitch", "https://www.twitch.tv/{handle}"),
    ("YouTube", "https://www.youtube.com/@{handle}"),
    ("Linktree", "https://linktr.ee/{handle}"),
)


def run(console: Console, config: dict[str, Any], dry_run: bool) -> None:
    _ = config, dry_run
    info(
        console,
        "Type YOUR username or email only.\n"
        "This checks public profile URLs (HTTP status). 200 is not proof of an account.",
    )
    from rich.prompt import Prompt

    raw = Prompt.ask("Your handle or email")
    try:
        ident = validate_own_identifier(raw)
    except ValueError as exc:
        error(console, str(exc))
        return

    if "@" in ident:
        digest = hashlib.md5(ident.strip().lower().encode("utf-8"), usedforsecurity=False).hexdigest()
        gravatar = f"https://www.gravatar.com/avatar/{digest}?d=404"
        status, _body, final = http_get(gravatar, headers={"User-Agent": USER_AGENT}, timeout=8.0)
        table = Table(title="Email (Gravatar only)")
        table.add_column("Check")
        table.add_column("Result")
        table.add_row("Gravatar", "public image exists" if status == 200 else f"no image (HTTP {status})")
        table.add_row("URL", final)
        console.print(table)
        console.print("[dim]Gravatar uses a hash of your email. Other breach DBs are menu 8.[/]")
        return

    table = Table(title=f"Public URLs for {ident}")
    table.add_column("Site")
    table.add_column("HTTP")
    table.add_column("URL")
    for site, template in SITES:
        url = template.format(handle=ident)
        try:
            status, _body, final = http_get(url, headers={"User-Agent": USER_AGENT}, timeout=8.0)
            mark = str(status)
        except OSError as exc:
            mark = "err"
            final = str(exc)
        table.add_row(site, mark, final if mark != "err" else url)
        time.sleep(0.25)
    console.print(table)
    warn(
        console,
        "HTTP 200 can be a soft 404 page. Open only YOUR links if you want to lock them down.",
    )
