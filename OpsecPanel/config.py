"""Load 66-Tool preferences from YAML, with environment overrides."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.yaml"
EXAMPLE_PATH = ROOT / "config.example.yaml"
WORDLIST_PATH = ROOT / "wordlists" / "eff_short_wordlist.txt"

DEFAULTS: dict[str, Any] = {
    "output_dir": "./output",
    "default_scrub_dir": "",
    "shred": {"passes": 3},
    "password": {
        "length": 20,
        "letters": True,
        "digits": True,
        "symbols": True,
        "passphrase_words": 6,
    },
    "hibp": {
        "api_key": "",
        "user_agent": "66-Tool (personal privacy hygiene tool)",
    },
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def ensure_config_file() -> Path:
    """Create config.yaml from the example if it is missing."""
    if not CONFIG_PATH.exists() and EXAMPLE_PATH.exists():
        shutil.copy(EXAMPLE_PATH, CONFIG_PATH)
    return CONFIG_PATH


def load_config() -> dict[str, Any]:
    ensure_config_file()
    data: dict[str, Any] = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raw = {}
        data = _deep_merge(DEFAULTS, raw)

    env_key = os.environ.get("HIBP_API_KEY", "").strip()
    if env_key:
        data.setdefault("hibp", {})["api_key"] = env_key
    if os.environ.get("TOOL66_OUTPUT_DIR"):
        data["output_dir"] = os.environ["TOOL66_OUTPUT_DIR"]
    if os.environ.get("TOOL66_SCRUB_DIR"):
        data["default_scrub_dir"] = os.environ["TOOL66_SCRUB_DIR"]

    shred = data.setdefault("shred", {})
    try:
        shred["passes"] = max(1, int(shred.get("passes", 3)))
    except (TypeError, ValueError):
        shred["passes"] = 3

    pw = data.setdefault("password", {})
    try:
        pw["length"] = max(4, int(pw.get("length", 20)))
    except (TypeError, ValueError):
        pw["length"] = 20
    try:
        pw["passphrase_words"] = max(3, int(pw.get("passphrase_words", 6)))
    except (TypeError, ValueError):
        pw["passphrase_words"] = 6

    return data


def resolve_output_dir(config: dict[str, Any]) -> Path:
    raw = str(config.get("output_dir") or "./output")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (ROOT / path).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path
