"""Run a 66-Tool module and optionally record it in the session."""

from __future__ import annotations

from typing import Any

from .modules import cert as cert_mod
from .modules import dns as dns_mod
from .modules import email as email_mod
from .modules import headers as headers_mod
from .modules import ip as ip_mod
from .modules import meta as meta_mod
from .modules import report as report_mod
from .modules import subdomains as subdomains_mod
from .modules import username as username_mod
from .modules import wayback as wayback_mod
from .modules import whois as whois_mod
from .result import Result
from . import session

MODULES = (
    "dns",
    "whois",
    "headers",
    "cert",
    "subdomains",
    "ip",
    "username",
    "email",
    "meta",
    "wayback",
    "report",
)

FORMATTERS = {
    "cert": cert_mod.format_text,
    "dns": dns_mod.format_text,
    "email": email_mod.format_text,
    "headers": headers_mod.format_text,
    "ip": ip_mod.format_text,
    "meta": meta_mod.format_text,
    "report": report_mod.format_text,
    "subdomains": subdomains_mod.format_text,
    "username": username_mod.format_text,
    "wayback": wayback_mod.format_text,
    "whois": whois_mod.format_text,
}


def format_text(result: Result) -> str:
    formatter = FORMATTERS.get(result.module)
    if formatter and result.data:
        return formatter(result.data)
    return ""


def run(module: str, timeout: float = 10.0, **fields: Any) -> Result:
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if module == "dns":
        return dns_mod.lookup(str(fields["domain"]), timeout)
    if module == "whois":
        return whois_mod.lookup(str(fields["domain"]), timeout)
    if module == "headers":
        return headers_mod.lookup(str(fields["url"]), timeout)
    if module == "cert":
        port = fields.get("port")
        port_value = int(port) if port not in (None, "", 0) else None
        return cert_mod.lookup(str(fields["host"]), timeout, port=port_value)
    if module == "subdomains":
        limit = int(fields.get("limit") or 200)
        return subdomains_mod.lookup(str(fields["domain"]), timeout, limit=limit)
    if module == "ip":
        return ip_mod.lookup(str(fields["target"]), timeout)
    if module == "username":
        return username_mod.lookup(str(fields["handle"]), timeout)
    if module == "email":
        return email_mod.lookup(str(fields["address"]), timeout)
    if module == "meta":
        return meta_mod.lookup(str(fields["path"]))
    if module == "wayback":
        limit = int(fields.get("limit") or 25)
        return wayback_mod.lookup(str(fields["url"]), timeout, limit=limit)
    if module == "report":
        out = str(fields.get("out") or "66-tool-report")
        return report_mod.lookup(out, clear_session=bool(fields.get("clear")))
    raise ValueError(f"unknown module: {module}")


def run_and_record(module: str, timeout: float = 10.0, **fields: Any) -> Result:
    result = run(module, timeout, **fields)
    if module != "report":
        session.record(result)
    return result
