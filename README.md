# 66-Tool

Free Windows privacy hygiene panel by **Ashh66**.

It only touches files and checks that belong to you: your metadata, your files, your own breach lookup, one URL you paste. It is not an exploit kit. There is no network scanning, port scanning, packet sniffing, or remote access.

Source is MIT. Download is this repo. No payment.

Site: https://ashh66.dev

## Requirements

- Windows
- Python 3.11 or newer
- Packages in `OpsecPanel/requirements.txt` (`rich`, `PyYAML`, `Pillow`, `pypdf`)

## Install

```cmd
git clone https://github.com/Ashhhh66/66-Tool.git
cd /d 66-Tool\OpsecPanel
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
Launch-66-Tool.cmd
```

`config.yaml` is created from `config.example.yaml` on first launch if it is missing. Do not commit `config.yaml`.

Optional environment variables (they override the YAML file):

| Variable | Purpose |
| --- | --- |
| `TOOL66_OUTPUT_DIR` | Default output directory |
| `TOOL66_SCRUB_DIR` | Default folder offered by the metadata scrubber |

Desktop shortcuts, if you want them:

```cmd
cd /d 66-Tool\OpsecPanel
install-shortcut.cmd
```

That adds **66 Tool** and **66 Tool Launcher**. You can pin either one to the taskbar.

## Use

`Launch-66-Tool.cmd` opens the CMD menu. You can also run:

```cmd
python main.py
```

Type a number and press Enter. `n` is the next page, `p` is the previous page. Press Enter after a tool to return to the menu. `h` is help. `0` or `q` quits.

Run one tool and quit:

```cmd
python main.py 14
python main.py 4
```

Preview destructive work without changing anything:

```cmd
python main.py --dry-run
python main.py 3 --dry-run
```

`--dry-run` is also respected inside shred, clean, startup-disable, and browser-clean. Those list targets and stop.

## Tools

| # | Tool | What it does |
| --- | --- | --- |
| 1 | Metadata Scrubber | Strip EXIF from JPEG/PNG and document metadata from PDFs. Shows before and after. Folder batch is supported. Writes `.scrubbed` copies under `output/` unless you confirm overwrite. |
| 2 | Network Leak Checker | Your public IP, your DNS servers, VPN-like adapter names, and a Tor check for this IP. |
| 3 | Secure File Shredder | Overwrite files, then delete them. Asks first. Works on a folder if you confirm. |
| 4 | Password / Passphrase Generator | Passwords and diceware-style phrases. Prints an entropy estimate. |
| 5 | Browser Fingerprint Info | What fingerprinting is and where to test it. This CLI has no browser canvas. |
| 6 | Local Log / History Cleaner | Your shell history, your temp files, your clipboard. Each one is confirmed separately. |
| 7 | File Integrity Checker | SHA-256 of a file, checked against a hash you paste. |
| 8 | Breach Check | One email you type, against the free XposedOrNot API. No API key. |
| 9 | Password Leak Check | Have I Been Pwned k-anonymity. The password stays on this PC. Only a 5-character hash prefix is sent. |
| 10 | Link / Phishing Inspector | One URL you paste: hostname, punycode, redirects, TLS. Fetches that URL only. |
| 11 | PC Security Snapshot | Read-only: BitLocker, Microsoft Defender, firewall, recent hotfixes. |
| 12 | Startup Programs | Your startup entries. Optional disable of one HKCU value after you confirm. |
| 13 | Email (.eml) Check | A saved message: From, Return-Path, Reply-To, auth headers, links. |
| 15 | Download / Attachment Check | File type versus filename, Office macros, double extensions. The file is not executed. |
| 16 | Wi-Fi / Network Hygiene | Current SSID, open versus WPA, your DNS. |
| 17 | Clipboard Watch | Preview the clipboard. Optional short watch for a swapped URL. |
| 18 | Account Hardening Checklist | Local ticks for 2FA, a unique password, and recovery codes. |
| 19 | App Privacy Snapshot | Camera, mic, and location consent for this Windows user. Read-only. |
| 20 | Browser Data Cleaner | Cache, cookies, or history in your Chrome, Edge, Brave, or Firefox profile. Confirm first. |
| 21 | Update Status | Your Python version, these packages versus PyPI, recent Windows hotfixes. Does not install anything. |
| 22 | Secret-in-Files Search | Scan a folder you own. Hits are masked. |
| 23 | Short Link / QR Expand | One short URL or QR image, expanded to the real destination. |
| 24 | Personal Footprint | Public profile URLs for your handle or email only. |

## Safety

Shred, overwrite, history delete, temp delete, clipboard clear, startup disable, and browser-data delete all default to **No**. They print what will change and wait for `y`.

Breach check (menu 8) is one email per run. Lists are rejected. Password check (menu 9) does not send the password.

## Public lookup CLI

The repo root also has a separate command, `66-tool`, for public DNS, WHOIS, headers, certificates, and similar lookups. It needs Python 3.9 or newer and no pip packages.

```cmd
cd /d 66-Tool
install-cmd.cmd
```

Open a new Command Prompt, then:

```cmd
66-tool -h
66-tool dns example.com
```

Use only public sources and data you are allowed to check.
