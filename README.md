# 66-Tool

Public-source desk by **Ashh66**.

Look up public records you are allowed to check. This is a lab and investigator helper, not an exploit kit.

## What it does

One CLI, many modules:

| Module | Looks up |
| --- | --- |
| `dns` | A / AAAA / MX / NS / TXT / CNAME |
| `whois` | Domain registration (port 43) |
| `headers` | Public HTTP response headers |
| `cert` | TLS dates, issuer, SANs |
| `subdomains` | Hostnames from public Certificate Transparency (crt.sh, then Cert Spotter) |
| `ip` | Reverse DNS + public RDAP (no port scan) |
| `username` | Public profile URLs for a handle; notes which return HTTP 200 |
| `email` | Syntax, Gravatar helpers, breach-lookup **links** only |
| `meta` | EXIF / metadata from a local file you provide |
| `wayback` | Public Wayback Machine CDX snapshots |
| `report` | JSON + markdown of the last run |

Every module prints the source used, a UTC timestamp, and `public data only`.

## Requirements

Python 3.9+ and the standard library. No pip packages.

The import package is `tool66` because a Python module name cannot start with a number or contain a hyphen.

## Use from CMD

Every module is already on one command: `66-tool`.

From this folder:

```cmd
cd /d E:\Omen-Tool
66-tool -h
66-tool dns example.com
66-tool whois example.com
66-tool headers https://example.com
66-tool cert example.com
66-tool subdomains example.com --timeout 30
66-tool ip 1.1.1.1
66-tool username ashh66
66-tool email lab@example.com
66-tool meta README.md
66-tool wayback https://example.com --limit 20 --timeout 30
66-tool report --out desk
```

To run `66-tool` from any folder, add this repo to your PATH once:

```cmd
cd /d E:\Omen-Tool
install-cmd.cmd
```

Then open a **new** Command Prompt and type `66-tool -h`.

## Desk in Command Prompt

```cmd
66-tool ui
```

That opens a menu in the same CMD window. Use the arrow keys and Enter, or type a number. Then type the domain / URL / handle and press Enter. Type `q` to quit.

No browser is used.

You can still call Python directly:

```cmd
python 66-tool.py dns example.com --json
python -m tool66 username ashh66
```

| Flag | Meaning |
| --- | --- |
| `--json` | Machine-readable output |
| `-t`, `--timeout` | Seconds to wait on network calls |
| `--out` | Report file prefix (`report` module) |
| `--clear` | Forget the last run (`report` module) |
| `--limit` | Cap CT names or Wayback rows |
| `--port` | TLS port for `cert` |

Exit codes: `0` ok, `1` failed lookup, `2` bad arguments.

`username` records HTTP 200, not a confirmed account. Some sites serve soft 404 pages.

`email` does not query breach databases. It prints pages where you can paste an address yourself if you are allowed to.

`ip` does not scan ports. Use Port-Scanner on hosts you own or have permission to test.

## Tests

```cmd
cd /d E:\Omen-Tool
set PYTHONPATH=.
python -m unittest discover -s tests -v
```

## Authorized use

Use only public sources and data you are allowed to check. Do not use 66-Tool to bypass logins, steal sessions, spray passwords, scrape paywalls, send unsolicited contact, or attack anyone. Unauthorized collection or access can be illegal.
