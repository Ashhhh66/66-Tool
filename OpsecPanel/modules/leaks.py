"""Self-check public IP, DNS resolver identity, and VPN/Tor heuristics."""

from __future__ import annotations

import json
import os
import socket
import struct
import subprocess
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from safety import USER_AGENT, http_get
from ui import error, info, warn

PUBLIC_IP_URLS = (
    "https://api.ipify.org",
    "https://ifconfig.me/ip",
)
TOR_CHECK_URL = "https://check.torproject.org/api/ip"
GOOGLE_WHOAMI = "o-o.myaddr.l.google.com"
RESOLVERS = (
    ("Cloudflare", "1.1.1.1"),
    ("Google", "8.8.8.8"),
    ("Quad9", "9.9.9.9"),
)
VPN_HINTS = (
    "tun",
    "tap",
    "wintun",
    "wireguard",
    "wg0",
    "nordlynx",
    "openvpn",
    "tailscale",
    "zerotier",
    "proton",
    "mullvad",
)


def _decode_name(data: bytes, offset: int) -> tuple[str, int]:
    labels: list[str] = []
    jumped = False
    return_at = offset
    hops = 0
    while offset < len(data) and hops < 20:
        length = data[offset]
        if length == 0:
            offset += 1
            break
        if length & 0xC0 == 0xC0:
            pointer = ((length & 0x3F) << 8) | data[offset + 1]
            if not jumped:
                return_at = offset + 2
                jumped = True
            offset = pointer
            hops += 1
            continue
        offset += 1
        labels.append(data[offset : offset + length].decode("ascii", "replace"))
        offset += length
    return ".".join(labels), (return_at if jumped else offset)


def dns_query(server: str, qname: str, qtype: int, timeout: float = 3.0) -> list[str]:
    """Minimal DNS A (1) / TXT (16) query to a public resolver. This host only."""
    import secrets

    tid = secrets.randbelow(65536)
    header = struct.pack("!HHHHHH", tid, 0x0100, 1, 0, 0, 0)
    qparts = b""
    for label in qname.strip(".").split("."):
        raw = label.encode("ascii")
        qparts += bytes([len(raw)]) + raw
    packet = header + qparts + b"\x00" + struct.pack("!HH", qtype, 1)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.settimeout(timeout)
        sock.sendto(packet, (server, 53))
        data, _ = sock.recvfrom(4096)
    finally:
        sock.close()
    if len(data) < 12:
        return []
    answers = struct.unpack("!H", data[6:8])[0]
    offset = 12
    _, offset = _decode_name(data, offset)
    offset += 4
    records: list[str] = []
    for _ in range(answers):
        _, offset = _decode_name(data, offset)
        if offset + 10 > len(data):
            break
        rtype, _rclass, _ttl, rdlen = struct.unpack("!HHIH", data[offset : offset + 10])
        offset += 10
        rdata = data[offset : offset + rdlen]
        offset += rdlen
        if rtype == 1 and len(rdata) == 4:
            records.append(socket.inet_ntoa(rdata))
        elif rtype == 16:
            chunks: list[str] = []
            i = 0
            while i < len(rdata):
                n = rdata[i]
                i += 1
                chunks.append(rdata[i : i + n].decode("utf-8", "replace"))
                i += n
            records.append("".join(chunks))
    return records


def system_resolver_txt(name: str) -> list[str]:
    try:
        answers = socket.getaddrinfo(name, None, socket.AF_INET, socket.SOCK_STREAM)
        return sorted({item[4][0] for item in answers})
    except socket.gaierror as exc:
        return [f"(system resolver error: {exc})"]


def _system_dns_servers() -> list[str]:
    servers: list[str] = []
    if os.name == "nt":
        try:
            out = subprocess.check_output(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-DnsClientServerAddress -AddressFamily IPv4 | "
                    "Select-Object -ExpandProperty ServerAddresses",
                ],
                text=True,
                timeout=8,
                stderr=subprocess.DEVNULL,
            )
            for line in out.splitlines():
                ip = line.strip()
                if ip and ip not in servers:
                    servers.append(ip)
        except (OSError, subprocess.SubprocessError):
            pass
        if not servers:
            try:
                out = subprocess.check_output(
                    ["ipconfig", "/all"],
                    text=True,
                    timeout=8,
                    encoding="oem",
                    errors="replace",
                )
                capture = False
                for line in out.splitlines():
                    if "DNS Servers" in line:
                        capture = True
                        part = line.split(":", 1)[-1].strip()
                        if part:
                            servers.append(part)
                    elif capture:
                        stripped = line.strip()
                        if not stripped or ":" in line[:40]:
                            capture = False
                        elif stripped not in servers:
                            servers.append(stripped)
            except (OSError, subprocess.SubprocessError):
                pass
    else:
        resolv = Path("/etc/resolv.conf")
        try:
            text = resolv.read_text(encoding="utf-8", errors="replace") if resolv.is_file() else ""
        except OSError:
            text = ""
        for line in text.splitlines():
            if line.startswith("nameserver"):
                parts = line.split()
                if len(parts) >= 2:
                    servers.append(parts[1])
    return servers


def _adapter_hints() -> list[str]:
    names: list[str] = []
    if os.name == "nt":
        try:
            out = subprocess.check_output(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-NetAdapter | ForEach-Object { $_.Name + ' | ' + $_.InterfaceDescription + ' | ' + $_.Status }",
                ],
                text=True,
                timeout=8,
                stderr=subprocess.DEVNULL,
            )
            names = [line.strip() for line in out.splitlines() if line.strip()]
        except (OSError, subprocess.SubprocessError):
            try:
                out = subprocess.check_output(["ipconfig"], text=True, timeout=8, encoding="oem", errors="replace")
                names = [line.strip() for line in out.splitlines() if "adapter" in line.lower()]
            except (OSError, subprocess.SubprocessError):
                pass
    else:
        try:
            out = subprocess.check_output(["ip", "-o", "link"], text=True, timeout=8, stderr=subprocess.DEVNULL)
            names = [line.strip() for line in out.splitlines() if line.strip()]
        except (OSError, subprocess.SubprocessError):
            pass
    return names


def _vpn_matches(adapter_lines: list[str]) -> list[str]:
    hits = []
    for line in adapter_lines:
        lower = line.lower()
        if any(hint in lower for hint in VPN_HINTS):
            hits.append(line)
    return hits


def _fetch_ip(url: str) -> str:
    status, body, _ = http_get(url, timeout=8.0)
    if status != 200:
        return f"(HTTP {status})"
    return body.decode("utf-8", "replace").strip().splitlines()[0].strip()


def run(console: Console, config: dict[str, Any], dry_run: bool) -> None:
    _ = config, dry_run
    info(
        console,
        "Checks this machine's public identity only.\n"
        "No port scans, no other hosts, no packet capture.",
    )

    ip_table = Table(title="Public IP (this host)")
    ip_table.add_column("Source")
    ip_table.add_column("Address")
    seen: list[str] = []
    for url in PUBLIC_IP_URLS:
        try:
            value = _fetch_ip(url)
        except OSError as exc:
            value = f"(error: {exc})"
        ip_table.add_row(url, value)
        if value and not value.startswith("("):
            seen.append(value)
    console.print(ip_table)
    unique = list(dict.fromkeys(seen))
    v4 = [ip for ip in unique if ":" not in ip]
    v6 = [ip for ip in unique if ":" in ip]
    if v4 and v6:
        console.print(f"[green]Public IPv4:[/] {v4[0]}   [green]IPv6:[/] {v6[0]}  [dim](dual-stack, not a mismatch)[/]")
    elif len(unique) > 1:
        warn(console, "Public-IP sources disagreed. Compare with your VPN overlay IP.")
    elif unique:
        console.print(f"[green]Public IP:[/] {unique[0]}")

    dns_servers = _system_dns_servers()
    dns_table = Table(title="Operating system DNS servers")
    dns_table.add_column("Resolver")
    if dns_servers:
        for item in dns_servers:
            dns_table.add_row(item)
    else:
        dns_table.add_row("(could not read local DNS configuration)")
    console.print(dns_table)

    leak = Table(title=f"DNS TXT whoami ({GOOGLE_WHOAMI})")
    leak.add_column("Via")
    leak.add_column("Answer")
    try:
        sys_a = ", ".join(system_resolver_txt("example.com")) or "(none)"
        leak.add_row("System resolver A example.com", sys_a)
    except OSError as exc:
        leak.add_row("System resolver", str(exc))
    for label, ip in RESOLVERS:
        try:
            txts = dns_query(ip, GOOGLE_WHOAMI, 16)
            leak.add_row(f"{label} {ip} TXT", ", ".join(txts) or "(no TXT)")
        except OSError as exc:
            leak.add_row(f"{label} {ip}", str(exc))
    console.print(leak)
    console.print(
        "[dim]If a VPN is on, OS DNS should be the VPN's servers, not your ISP. "
        "TXT whoami answers show the address each public resolver sees.[/]"
    )

    adapters = _adapter_hints()
    hits = _vpn_matches(adapters)
    vpn_table = Table(title="Adapter names (VPN heuristic)")
    vpn_table.add_column("Interface")
    for line in (hits or adapters[:12] or ["(none listed)"]):
        vpn_table.add_row(line)
    console.print(vpn_table)
    if hits:
        console.print("[green]VPN-like adapter name found (heuristic, not proof).[/]")
    else:
        console.print("[yellow]No TUN/TAP/WireGuard-style adapter name spotted.[/]")

    try:
        status, body, _ = http_get(TOR_CHECK_URL, headers={"User-Agent": USER_AGENT}, timeout=8.0)
        if status == 200:
            payload = json.loads(body.decode("utf-8"))
            is_tor = payload.get("IsTor")
            tor_ip = payload.get("IP", "")
            style = "green" if is_tor else "yellow"
            console.print(f"[{style}]Tor check.torproject.org:[/] IsTor={is_tor}  IP={tor_ip}")
        else:
            warn(console, f"Tor check HTTP {status}")
    except (OSError, json.JSONDecodeError) as exc:
        error(console, f"Tor check failed: {exc}")

    console.print(
        Panel(
            "WebRTC leaks happen inside a browser, not this CLI.\n"
            "Open a browser (ideally the one you actually use) and visit:\n"
            "  https://browserleaks.com/webrtc\n"
            "  https://ipleak.net/\n"
            "Look for extra IPv4/IPv6 addresses besides your VPN/Tor exit. "
            "Disable WebRTC in the browser if you need that isolation.",
            title="WebRTC (manual browser check)",
            border_style="magenta",
        )
    )
