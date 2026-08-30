"""Check YOUR email against XposedOrNot (free, no API key)."""

from __future__ import annotations

import json
import time
from typing import Any
from urllib.parse import quote

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from safety import USER_AGENT, http_get, validate_own_identifier
from ui import error, info, warn

CHECK_URL = "https://api.xposedornot.com/v1/check-email/{email}?details=true"
ANALYTICS_URL = "https://api.xposedornot.com/v1/breach-analytics?email={email}"
MIN_INTERVAL = 1.0


def _get(url: str) -> tuple[int, Any]:
    status, body, _ = http_get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=15.0,
    )
    if not body:
        return status, None
    try:
        return status, json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        return status, body.decode("utf-8", "replace")


def _flatten_names(payload: Any) -> list[str]:
    names: list[str] = []
    if not isinstance(payload, dict):
        return names
    raw = payload.get("breaches")
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, list):
                names.extend(str(x) for x in item if x)
            elif item:
                names.append(str(item))
    return names


def _detail_rows(payload: Any) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    if not isinstance(payload, dict):
        return rows

    details = payload.get("breach_details")
    if isinstance(details, list):
        for item in details:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "?")
            date = str(item.get("breach_date") or item.get("year") or "?") or "?"
            data = item.get("exposed_data") or item.get("xposed_data") or ""
            if isinstance(data, list):
                data = ", ".join(str(x) for x in data)
            else:
                data = str(data).replace(";", ", ")
            rows.append((name, date if date.strip() else "?", data or "?"))
        if rows:
            return rows

    exposed = payload.get("ExposedBreaches") or payload.get("exposedBreaches") or {}
    block: Any = []
    if isinstance(exposed, dict):
        block = (
            exposed.get("breaches_details")
            or exposed.get("Breaches_Details")
            or exposed.get("exposedBreaches")
            or []
        )
    elif isinstance(exposed, list):
        block = exposed
    if not isinstance(block, list):
        return rows
    for item in block:
        if not isinstance(item, dict):
            continue
        name = str(
            item.get("breach")
            or item.get("breachID")
            or item.get("name")
            or "?"
        )
        date = str(item.get("xposed_date") or item.get("breached_date") or "?")
        data = item.get("xposed_data") or item.get("exposed_data") or ""
        if isinstance(data, list):
            data = ", ".join(str(x) for x in data)
        else:
            data = str(data).replace(";", ", ")
        rows.append((name, date, data or "?"))
    return rows


def run(console: Console, config: dict[str, Any], dry_run: bool) -> None:
    _ = config, dry_run
    info(
        console,
        "Uses XposedOrNot (free, no API key) for ONE email you type now.\n"
        "Do not enter other people's addresses. Lists and files are rejected.\n"
        "Same job as Have I Been Pwned: were you in known public breaches?",
    )
    raw = Prompt.ask("Your email (this session only)")
    try:
        account = validate_own_identifier(raw)
    except ValueError as exc:
        error(console, str(exc))
        return
    if "@" not in account:
        error(console, "This free check is email-only. Type an address like you@example.com.")
        return

    encoded = quote(account, safe="")
    console.print("[dim]Checking XposedOrNot (rate-limited)…[/]")
    status, payload = _get(CHECK_URL.format(email=encoded))

    if status == 429:
        error(console, "XposedOrNot rate-limited this IP (HTTP 429). Wait and try again.")
        return
    if isinstance(payload, dict) and str(payload.get("Error") or "").lower() == "not found":
        console.print("[bold green]No breaches[/] listed for that email.")
        return
    if status not in {200, 201} or not isinstance(payload, dict):
        error(console, f"XposedOrNot HTTP {status}: {payload!r}"[:400])
        return

    rows = _detail_rows(payload)
    names = _flatten_names(payload)
    if not rows and names:
        time.sleep(MIN_INTERVAL)
        astatus, analytics = _get(ANALYTICS_URL.format(email=encoded))
        if astatus == 200:
            rows = _detail_rows(analytics)

    if rows:
        table = Table(title=f"Breaches for {account} (XposedOrNot)")
        table.add_column("Name")
        table.add_column("Year")
        table.add_column("Data types")
        for name, date, data in rows:
            table.add_row(name, date, data)
        console.print(table)
        console.print(f"[bold]{len(rows)}[/] breach record(s). Change reused passwords if any were exposed.")
    elif names:
        table = Table(title=f"Breaches for {account} (XposedOrNot)")
        table.add_column("Name")
        for name in names:
            table.add_row(name)
        console.print(table)
        console.print(f"[bold]{len(names)}[/] breach name(s).")
    else:
        console.print("[bold green]No breaches[/] listed for that email.")

    console.print(
        "[dim]Source: xposedornot.com (free). Coverage is public breaches, not a guarantee "
        "every dump is listed.[/]"
    )
