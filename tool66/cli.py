"""Command-line interface for Ashh66 66-Tool."""

from __future__ import annotations

import argparse
import sys

from .dispatch import run as run_module
from .output import print_result
from .result import Result
from . import session
from .tui import run_desk


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Print machine-readable JSON",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=float,
        default=10.0,
        help="Network timeout in seconds (default: 10)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="66-tool",
        description=(
            "Ashh66 66-Tool. Look up public data you are allowed to check. "
            "Lab and investigator helper, not an exploit kit."
        ),
    )
    _common(parser)
    sub = parser.add_subparsers(dest="module", required=True)

    dns_p = sub.add_parser("dns", help="A/AAAA/MX/NS/TXT/CNAME for a domain")
    _common(dns_p)
    dns_p.add_argument("domain", help="Domain name")

    whois_p = sub.add_parser("whois", help="Domain registration lookup")
    _common(whois_p)
    whois_p.add_argument("domain", help="Domain name")

    headers_p = sub.add_parser("headers", help="Public HTTP response headers")
    _common(headers_p)
    headers_p.add_argument("url", help="http(s) URL")

    cert_p = sub.add_parser("cert", help="TLS certificate dates, issuer, SANs")
    _common(cert_p)
    cert_p.add_argument("host", help="Hostname or host:port")
    cert_p.add_argument("--port", type=int, help="TLS port (default: 443)")

    sub_p = sub.add_parser("subdomains", help="Names from public Certificate Transparency")
    _common(sub_p)
    sub_p.add_argument("domain", help="Domain name")
    sub_p.add_argument("--limit", type=int, default=200, help="Max names to keep")

    ip_p = sub.add_parser("ip", help="Reverse DNS and public IP info (no port scan)")
    _common(ip_p)
    ip_p.add_argument("target", help="IP address or hostname")

    user_p = sub.add_parser("username", help="Public profile URLs for a handle")
    _common(user_p)
    user_p.add_argument("handle", help="Public handle")

    email_p = sub.add_parser("email", help="Syntax, Gravatar helpers, breach lookup links")
    _common(email_p)
    email_p.add_argument("address", help="Email address")

    meta_p = sub.add_parser("meta", help="EXIF/metadata from a local file")
    _common(meta_p)
    meta_p.add_argument("path", help="Local file you are allowed to inspect")

    way_p = sub.add_parser("wayback", help="Public Wayback/CDX snapshots")
    _common(way_p)
    way_p.add_argument("url", help="http(s) URL")
    way_p.add_argument("--limit", type=int, default=25, help="Max snapshots (1-100)")

    report_p = sub.add_parser("report", help="Write JSON + markdown of the last run")
    _common(report_p)
    report_p.add_argument(
        "--out",
        default="66-tool-report",
        help="Output prefix (default: 66-tool-report)",
    )
    report_p.add_argument(
        "--clear",
        action="store_true",
        help="Forget the last run instead of writing a report",
    )

    ui_p = sub.add_parser("ui", help="Interactive desk in this Command Prompt")
    _common(ui_p)
    return parser


def _run_module(args: argparse.Namespace) -> Result:
    fields: dict = {}
    if args.module == "dns":
        fields = {"domain": args.domain}
    elif args.module == "whois":
        fields = {"domain": args.domain}
    elif args.module == "headers":
        fields = {"url": args.url}
    elif args.module == "cert":
        fields = {"host": args.host, "port": args.port}
    elif args.module == "subdomains":
        fields = {"domain": args.domain, "limit": args.limit}
    elif args.module == "ip":
        fields = {"target": args.target}
    elif args.module == "username":
        fields = {"handle": args.handle}
    elif args.module == "email":
        fields = {"address": args.address}
    elif args.module == "meta":
        fields = {"path": args.path}
    elif args.module == "wayback":
        fields = {"url": args.url, "limit": args.limit}
    elif args.module == "report":
        fields = {"out": args.out, "clear": args.clear}
    else:
        raise ValueError(f"unknown module: {args.module}")
    return run_module(args.module, args.timeout, **fields)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code
        if code is None:
            return 0
        return int(code) if str(code).isdigit() else 2

    if args.timeout <= 0:
        print("error: timeout must be positive", file=sys.stderr)
        return 2

    if args.module == "ui":
        return run_desk()

    try:
        result = _run_module(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.module != "report":
        try:
            session.record(result)
        except OSError as exc:
            print(f"error: could not save session: {exc}", file=sys.stderr)

    print_result(result, args.as_json)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
