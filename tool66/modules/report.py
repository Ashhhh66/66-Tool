"""Write a JSON + markdown report of the last 66-Tool run."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..result import BANNER, NOTICE, OPERATOR, PRODUCT, Result
from .. import session


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# {BANNER} report",
        "",
        f"- Operator: {payload.get('operator', OPERATOR)}",
        f"- Product: {payload.get('product', PRODUCT)}",
        f"- Notice: {payload.get('notice', NOTICE)}",
        f"- Updated: {payload.get('updated_utc', '')}",
        f"- Runs: {len(payload.get('runs') or [])}",
        "",
    ]
    for index, run in enumerate(payload.get("runs") or [], start=1):
        if not isinstance(run, dict):
            continue
        lines.extend(
            [
                f"## {index}. {run.get('module', 'unknown')} — {run.get('target', '')}",
                "",
                f"- Source: {run.get('source', '')}",
                f"- Time: {run.get('timestamp_utc', '')}",
                f"- Notice: {run.get('notice', NOTICE)}",
                f"- OK: {run.get('ok', False)}",
            ]
        )
        if run.get("error"):
            lines.append(f"- Error: {run['error']}")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(run.get("data") or {}, indent=2))
        lines.append("```")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def lookup(out_prefix: str, clear_session: bool = False) -> Result:
    if clear_session:
        existed = session.clear()
        return Result(
            module="report",
            source="local session file",
            target=str(session.session_path()),
            ok=True,
            data={"cleared": existed, "path": str(session.session_path())},
        )

    payload = session.load()
    if payload is None:
        return Result(
            module="report",
            source="local session file",
            target=str(session.session_path()),
            ok=False,
            error="no last run to report (run another module first)",
        )

    prefix = Path(out_prefix)
    if prefix.suffix:
        json_path = prefix
        md_path = prefix.with_suffix(".md")
    else:
        json_path = Path(f"{prefix}.json")
        md_path = Path(f"{prefix}.md")

    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(_markdown(payload), encoding="utf-8")
    return Result(
        module="report",
        source="local session file",
        target=str(session.session_path()),
        ok=True,
        data={
            "updated_utc": payload.get("updated_utc"),
            "runs": len(payload.get("runs") or []),
            "json_path": str(json_path),
            "markdown_path": str(md_path),
        },
    )


def format_text(data: dict[str, Any]) -> str:
    if data.get("cleared") is not None:
        return f"cleared  {data.get('cleared')}\npath     {data.get('path', '')}"
    return (
        f"runs     {data.get('runs', 0)}\n"
        f"json     {data.get('json_path', '')}\n"
        f"markdown {data.get('markdown_path', '')}"
    )
