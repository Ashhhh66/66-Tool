"""Cryptographically secure passwords and Diceware-style passphrases."""

from __future__ import annotations

import math
import secrets
import string
from typing import Any

from rich.console import Console
from rich.prompt import IntPrompt, Prompt
from rich.table import Table

from config import WORDLIST_PATH
from ui import ask_yes_no, error, info, warn

SYMBOLS = "!@#$%^&*()-_=+[]{};:,.?"


def load_words() -> list[str]:
    if not WORDLIST_PATH.is_file():
        raise FileNotFoundError(f"Word list missing: {WORDLIST_PATH}")
    words: list[str] = []
    for line in WORDLIST_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        words.append(parts[-1] if parts else line)
    if len(words) < 100:
        raise ValueError("Word list is too small to use for passphrases.")
    return words


def entropy_bits(choices: int, length: int) -> float:
    if choices <= 1 or length <= 0:
        return 0.0
    return length * math.log2(choices)


def strength_label(bits: float) -> str:
    if bits < 40:
        return "weak"
    if bits < 60:
        return "fair"
    if bits < 80:
        return "strong"
    return "very strong"


def build_alphabet(*, letters: bool, digits: bool, symbols: bool) -> str:
    alpha = ""
    if letters:
        alpha += string.ascii_letters
    if digits:
        alpha += string.digits
    if symbols:
        alpha += SYMBOLS
    if not alpha:
        raise ValueError("Select at least one character set.")
    return alpha


def generate_password(length: int, alphabet: str) -> str:
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_passphrase(words: int, wordlist: list[str], *, separator: str = "-") -> str:
    return separator.join(secrets.choice(wordlist) for _ in range(words))


def _show(console: Console, value: str, bits: float, detail: str) -> None:
    table = Table(title="Generated secret")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Secret", value)
    table.add_row("Entropy (estimate)", f"{bits:.1f} bits")
    table.add_row("Strength", strength_label(bits))
    table.add_row("Model", detail)
    console.print(table)
    console.print("[dim]Estimate assumes an attacker who knows the generator settings.[/]")


def run(console: Console, config: dict[str, Any], dry_run: bool) -> None:
    _ = dry_run
    pw = config.get("password", {})
    info(
        console,
        "Uses the secrets module (CSPRNG), not random.\n"
        "Diceware mode uses the bundled EFF short word list.",
    )
    mode = Prompt.ask("Mode: [1] password  [2] passphrase", default="1").strip()
    if mode == "2":
        wordlist = load_words()
        n = IntPrompt.ask("Number of words", default=int(pw.get("passphrase_words", 6)))
        n = max(3, int(n))
        phrase = generate_passphrase(n, wordlist)
        bits = entropy_bits(len(wordlist), n)
        _show(console, phrase, bits, f"Diceware, {n} words from {len(wordlist)}-word list")
        return

    length = IntPrompt.ask("Length", default=int(pw.get("length", 20)))
    length = max(4, int(length))
    letters = ask_yes_no(console, "Include letters?", default=bool(pw.get("letters", True)))
    digits = ask_yes_no(console, "Include digits?", default=bool(pw.get("digits", True)))
    symbols = ask_yes_no(console, "Include symbols?", default=bool(pw.get("symbols", True)))
    try:
        alphabet = build_alphabet(letters=letters, digits=digits, symbols=symbols)
    except ValueError as exc:
        error(console, str(exc))
        return
    secret = generate_password(length, alphabet)
    bits = entropy_bits(len(alphabet), length)
    _show(console, secret, bits, f"uniform from {len(alphabet)}-character alphabet")
    if not letters or not digits:
        warn(console, "Narrow character sets reduce entropy for the same length.")
