"""Text and JSON printing for 66-Tool results."""

from __future__ import annotations

import json

from .dispatch import format_text
from .result import BANNER, NOTICE, Result


def print_result(result: Result, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result.to_payload(), indent=2))
        return
    print(BANNER)
    print(f"{'module':<8} {result.module}")
    print(f"{'source':<8} {result.source}")
    print(f"{'time':<8} {result.timestamp_utc}")
    print(f"{'notice':<8} {NOTICE}")
    print(f"{'target':<8} {result.target}")
    if result.error:
        print(f"{'error':<8} {result.error}")
    print()
    text = format_text(result)
    if text:
        print(text)
    elif result.data:
        print(json.dumps(result.data, indent=2))
