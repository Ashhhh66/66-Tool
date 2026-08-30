"""Explain browser fingerprinting and how to check it (CLI has no browser)."""

from __future__ import annotations

import sys
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from safety import USER_AGENT
from ui import info

GUIDE = """\
Browser fingerprinting is a way sites recognize a browser from **many small
signals combined**, even without cookies: User-Agent, screen size, time zone,
installed fonts, canvas/WebGL rendering, audio stack, language, and more.

This is a **command-line** tool. It cannot see your browser's canvas, fonts,
or WebGL. Checking a fingerprint requires opening a real browser profile.

**How to check (manual):**

1. Use the same browser (and profile) you care about — not a throwaway window
   if you want an accurate picture of daily browsing.
2. Visit a test site, for example:
   - https://coveryourtracks.eff.org/
   - https://amiunique.org/
   - https://browserleaks.com/
3. Read uniqueness / bits of identifying info. Lower uniqueness is better if
   you are trying to blend in.
4. Compare a privacy-focused browser (or strict tracking protection) vs your
   everyday profile.

**What this CLI can show:** only strings *this process* would send, which is
**not** your browser fingerprint.
"""


def run(console: Console, config: dict[str, Any], dry_run: bool) -> None:
    _ = config, dry_run
    info(console, "Educational. No network probe of other people or sites beyond what you open yourself.")
    console.print(Markdown(GUIDE))

    table = Table(title="This process (not your browser)")
    table.add_column("Signal")
    table.add_column("Value")
    table.add_row("Python", sys.version.split()[0])
    table.add_row("Platform", sys.platform)
    table.add_row("HTTPS User-Agent we send", USER_AGENT)
    table.add_row("Browser User-Agent", "(none — no browser context)")
    table.add_row("Canvas / WebGL / fonts", "(unavailable in CLI)")
    console.print(table)
    console.print(
        Panel(
            "If you opened this from a browser-based terminal, that still does not "
            "expose the browser's fingerprint APIs to Python.",
            border_style="dim",
        )
    )
