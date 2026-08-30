"""Clear cache / cookies / history in YOUR browser profiles only."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from safety import assert_user_path, format_size
from ui import ask_yes_no, confirm_destructive, info, warn

SKIP_PROFILES = {"System Profile", "Guest Profile", "Crashpad"}


def _chromium_roots() -> list[tuple[str, Path]]:
    home = Path.home()
    return [
        ("Chrome", home / "AppData/Local/Google/Chrome/User Data"),
        ("Edge", home / "AppData/Local/Microsoft/Edge/User Data"),
        ("Brave", home / "AppData/Local/BraveSoftware/Brave-Browser/User Data"),
    ]


def _chromium_profiles(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    names = {"Default"}
    local_state = root / "Local State"
    if local_state.is_file():
        try:
            data = json.loads(local_state.read_text(encoding="utf-8"))
            info = data.get("profile", {}).get("info_cache", {})
            if isinstance(info, dict):
                names.update(info.keys())
        except (OSError, json.JSONDecodeError):
            pass
    found: list[Path] = []
    for name in sorted(names):
        if name in SKIP_PROFILES:
            continue
        path = root / name
        if path.is_dir():
            found.append(path)
    return found


def _firefox_profiles() -> list[Path]:
    root = Path.home() / "AppData/Roaming/Mozilla/Firefox/Profiles"
    if not root.is_dir():
        return []
    return sorted(p for p in root.iterdir() if p.is_dir())


def _gather_targets(profile: Path, *, cache: bool, cookies: bool, history: bool) -> list[Path]:
    names: list[str] = []
    if cache:
        names.extend(
            [
                "Cache",
                "Code Cache",
                "GPUCache",
                "Service Worker/CacheStorage",
                "cache2",
            ]
        )
    if cookies:
        names.extend(["Cookies", "Cookies-journal", "Network/Cookies", "cookies.sqlite"])
    if history:
        names.extend(["History", "History-journal", "places.sqlite"])
    out: list[Path] = []
    for name in names:
        path = profile / name
        if path.exists():
            out.append(path)
    return out


def _walk_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            for child in path.rglob("*"):
                if child.is_file():
                    files.append(child)
    return files


def run(console: Console, config: dict[str, Any], dry_run: bool) -> None:
    _ = config
    info(
        console,
        "Current user browser profiles only. Close the browser first.\n"
        "Cookies / history log you out of sites. Cache is the safer first pick.",
    )
    catalog: list[tuple[str, Path]] = []
    for label, root in _chromium_roots():
        try:
            root = assert_user_path(root)
        except PermissionError:
            continue
        for profile in _chromium_profiles(root):
            catalog.append((f"{label} / {profile.name}", profile))
    try:
        fx_root = Path.home() / "AppData/Roaming/Mozilla/Firefox/Profiles"
        assert_user_path(fx_root)
        for profile in _firefox_profiles():
            catalog.append((f"Firefox / {profile.name}", profile))
    except (PermissionError, FileNotFoundError):
        pass

    if not catalog:
        warn(console, "No Chrome / Edge / Brave / Firefox profiles found under your account.")
        return

    table = Table(title="Your profiles")
    table.add_column("#", style="dim")
    table.add_column("Profile")
    table.add_column("Path")
    for i, (label, path) in enumerate(catalog, start=1):
        table.add_row(str(i), label, str(path))
    console.print(table)
    pick = Prompt.ask("Profile number", default="").strip()
    try:
        label, profile = catalog[int(pick) - 1]
    except (ValueError, IndexError):
        warn(console, "Not a valid number.")
        return

    cache = ask_yes_no(console, "Include cache?", default=True)
    cookies = ask_yes_no(console, "Include cookies (logs you out)?", default=False)
    history = ask_yes_no(console, "Include browsing history DB?", default=False)
    if not (cache or cookies or history):
        warn(console, "Nothing selected.")
        return

    targets = _gather_targets(profile, cache=cache, cookies=cookies, history=history)
    files = _walk_files(targets)
    total = 0
    for path in files:
        try:
            total += path.stat().st_size
        except OSError:
            pass
    console.print(f"{label}: {len(files)} file(s), {format_size(total)}")
    ok = confirm_destructive(
        console,
        f"Delete the selected browser data under {profile}. Locked files will be skipped.",
        files,
        total_bytes=total,
        dry_run=dry_run,
    )
    if not ok:
        return
    deleted = skipped = 0
    for path in files:
        try:
            path.unlink()
            deleted += 1
        except OSError:
            skipped += 1
    console.print(f"[green]Deleted {deleted}[/], skipped {skipped} (browser still open?).")
