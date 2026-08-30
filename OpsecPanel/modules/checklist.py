"""Personal account-hardening checklist stored on this machine only."""

from __future__ import annotations

from typing import Any

import yaml
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from config import ROOT
from ui import ask_yes_no, info, warn

CHECKLIST_PATH = ROOT / "checklist.yaml"

DEFAULT_ACCOUNTS = (
    "Email",
    "Google / Apple / Microsoft",
    "Bank / payments",
    "Social",
    "GitHub / code",
    "Gaming",
)

FIELDS = (
    ("two_factor", "2FA / passkey"),
    ("unique_password", "Unique password"),
    ("recovery_codes", "Recovery codes saved"),
    ("app_passwords", "Old app passwords revoked"),
)


def _load() -> list[dict[str, Any]]:
    if not CHECKLIST_PATH.is_file():
        return [
            {
                "name": name,
                "two_factor": False,
                "unique_password": False,
                "recovery_codes": False,
                "app_passwords": False,
            }
            for name in DEFAULT_ACCOUNTS
        ]
    raw = yaml.safe_load(CHECKLIST_PATH.read_text(encoding="utf-8")) or {}
    accounts = raw.get("accounts") if isinstance(raw, dict) else raw
    if not isinstance(accounts, list):
        return [
            {
                "name": name,
                "two_factor": False,
                "unique_password": False,
                "recovery_codes": False,
                "app_passwords": False,
            }
            for name in DEFAULT_ACCOUNTS
        ]
    out: list[dict[str, Any]] = []
    for item in accounts:
        if not isinstance(item, dict) or not item.get("name"):
            continue
        out.append(
            {
                "name": str(item["name"]),
                "two_factor": bool(item.get("two_factor")),
                "unique_password": bool(item.get("unique_password")),
                "recovery_codes": bool(item.get("recovery_codes")),
                "app_passwords": bool(item.get("app_passwords")),
            }
        )
    return out or [
        {
            "name": name,
            "two_factor": False,
            "unique_password": False,
            "recovery_codes": False,
            "app_passwords": False,
        }
        for name in DEFAULT_ACCOUNTS
    ]


def _save(accounts: list[dict[str, Any]]) -> None:
    CHECKLIST_PATH.write_text(
        yaml.safe_dump({"accounts": accounts}, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _show(console: Console, accounts: list[dict[str, Any]]) -> None:
    table = Table(title="Your hardening list (this PC only)")
    table.add_column("#", style="dim", width=4)
    table.add_column("Account")
    for key, label in FIELDS:
        table.add_column(label)
    for i, item in enumerate(accounts, start=1):
        row = [str(i), str(item["name"])]
        for key, _label in FIELDS:
            row.append("yes" if item.get(key) else "no")
        table.add_row(*row)
    console.print(table)


def run(console: Console, config: dict[str, Any], dry_run: bool) -> None:
    _ = config
    info(
        console,
        "A private checklist for YOUR accounts. Nothing is sent to the internet.\n"
        f"Saved at {CHECKLIST_PATH.name} (gitignored).",
    )
    accounts = _load()
    _show(console, accounts)

    if ask_yes_no(console, "Add an account name?", default=False):
        name = Prompt.ask("Name").strip()
        if name:
            accounts.append(
                {
                    "name": name,
                    "two_factor": False,
                    "unique_password": False,
                    "recovery_codes": False,
                    "app_passwords": False,
                }
            )

    if ask_yes_no(console, "Toggle a checkbox?", default=True):
        pick = Prompt.ask("Account number", default="").strip()
        try:
            item = accounts[int(pick) - 1]
        except (ValueError, IndexError):
            warn(console, "Not a valid number.")
        else:
            field_table = Table(title=str(item["name"]))
            field_table.add_column("#")
            field_table.add_column("Field")
            field_table.add_column("Now")
            for i, (key, label) in enumerate(FIELDS, start=1):
                field_table.add_row(str(i), label, "yes" if item.get(key) else "no")
            console.print(field_table)
            which = Prompt.ask("Field number to toggle", default="").strip()
            try:
                key = FIELDS[int(which) - 1][0]
            except (ValueError, IndexError):
                warn(console, "Not a valid field.")
            else:
                item[key] = not bool(item.get(key))
                console.print(f"[green]{FIELDS[int(which) - 1][1]}[/] is now {'yes' if item[key] else 'no'}")

    if dry_run:
        warn(console, "Dry-run: checklist file not written.")
        _show(console, accounts)
        return
    _save(accounts)
    _show(console, accounts)
    console.print(f"[dim]Wrote {CHECKLIST_PATH}[/]")
