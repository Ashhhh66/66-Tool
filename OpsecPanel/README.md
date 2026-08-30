# 66-Tool

Personal **privacy and security hygiene** toolkit with an interactive CMD-style menu. It only touches files and data that belong to the current user, plus self-checks (your public IP, your DNS resolvers, your own Have I Been Pwned lookup).

This is **not** an exploit kit. There is no network scanning, port scanning, packet sniffing, credential harvesting, or remote access.

## Requirements

- Python **3.11+**
- pip packages in `requirements.txt` (`rich`, `PyYAML`, `Pillow`, `pypdf`)

## Setup

From this folder:

```cmd
cd /d E:\Omen-Tool\OpsecPanel
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy config.example.yaml config.yaml
```

On first launch, `config.yaml` is created from the example if it is missing. Keep secrets out of git (`config.yaml` is gitignored).

Optional environment overrides (win over YAML):

| Variable | Purpose |
| --- | --- |
| `TOOL66_OUTPUT_DIR` | Default output directory |
| `TOOL66_SCRUB_DIR` | Default path offered by the metadata scrubber |

## Usage

**Easiest:** double-click **66 Tool** on your Desktop (or `Launch-66-Tool.cmd` in this folder). That opens the CMD panel.

For a window with a Launch button, double-click **66 Tool Launcher** on the Desktop, or `Open-66-Tool-App.cmd`. You can pin either shortcut to the taskbar.

If shortcuts are missing:

```cmd
cd /d E:\Omen-Tool\OpsecPanel
install-shortcut.cmd
```

From a Command Prompt you already have:

```cmd
python main.py
```

You get a boxed **66 TOOL** menu (**page 1/2**). Type a number and press Enter. **`n`** goes to page 2, **`p`** back to page 1. After each tool, press Enter to return to the menu. `0` or `q` exits. `h` is help.

Run one item and quit:

```cmd
python main.py 14
python main.py 4
```

Preview destructive work without changing anything:

```cmd
python main.py --dry-run
python main.py 3 --dry-run
```

`--dry-run` is also respected inside shred, clean, startup-disable, and browser-clean: they list targets and stop.

## Tools

| # | Tool | What it does |
| --- | --- | --- |
| 1 | Metadata Scrubber | Strip EXIF from JPEG/PNG and document/XMP metadata from PDFs. Shows before/after. Folder batch supported. Writes `.scrubbed` copies under `output/` unless you confirm overwrite. |
| 2 | Network Leak Checker | Your public IP (two sources), OS DNS servers, TXT whoami via public resolvers, VPN-like adapter names, Tor Project check for *this* IP. WebRTC is explained for a manual browser test. |
| 3 | Secure File Shredder | Overwrite files with `secrets` random bytes N times, then delete. Confirms with paths and total size. Recursive for a folder. |
| 4 | Password / Passphrase Generator | CSPRNG passwords (`secrets`, not `random`) and Diceware-style phrases from the bundled [EFF short wordlist](https://www.eff.org/dice). Prints an entropy estimate. |
| 5 | Browser Fingerprint Info | What fingerprinting is and how to test it (Cover Your Tracks, etc.). The CLI has no browser canvas/WebGL/fonts. |
| 6 | Local Log / History Cleaner | Truncate **your** PowerShell / bash / zsh / Python history files, optionally delete files in **your** temp directory, empty **your** clipboard. Each category is confirmed separately. |
| 7 | File Integrity Checker | SHA-256 of a file; verify against a hash you paste (constant-time compare). Optional `.sha256` sidecar in `output/`. |
| 8 | Breach Check | One email **you type in this session** against the free [XposedOrNot](https://xposedornot.com/api_doc) API. No API key. |
| 9 | Password Leak Check | k-anonymity [Pwned Passwords](https://haveibeenpwned.com/Passwords): SHA-1 locally, only the first 5 hex chars are sent. No paid API key. Password is not echoed or stored. |
| 10 | Link / Phishing Inspector | One URL you paste: hostname, punycode, redirect chain, TLS cert, shape heuristics. Fetches that URL only. |
| 11 | PC Security Snapshot | Read-only Windows: BitLocker, Microsoft Defender, firewall profiles, recent hotfixes. |
| 12 | Startup Programs | Your HKCU Run/RunOnce values and Startup folder. Optional disable of one HKCU value after confirm. |
| 13 | Email (.eml) Check | Saved message: From vs Return-Path vs Reply-To, auth headers, links / tracking hints. |
| 15 | Download / Attachment Check | Magic bytes vs filename, Office macros, double extensions. File is not executed. |
| 16 | Wi-Fi / Network Hygiene | Current SSID, WPA vs open, OS DNS, reminder for cafe Wi-Fi. |
| 17 | Clipboard Watch | Preview clipboard; optional 20s watch for URL/address swaps. |
| 18 | Account Hardening Checklist | Local ticks for 2FA, unique password, recovery codes (saved in `checklist.yaml`). |
| 19 | App Privacy Snapshot | Camera, mic, location consent for this Windows user (read-only). |
| 20 | Browser Data Cleaner | Cache / cookies / history in your Chrome, Edge, Brave, or Firefox profile. Confirm + dry-run. |
| 21 | Update Status | Python version, 66-Tool packages vs PyPI, recent Windows hotfixes. Does not install. |
| 22 | Secret-in-Files Search | Scan a folder you own; hits are masked. |
| 23 | Short Link / QR Expand | One short URL or QR image to the real destination. Optional `pip install zxing-cpp` for QR. |
| 24 | Personal Footprint | Public profile URLs / Gravatar for **your** handle or email only. |
| n / p | Pages | Next / previous menu page. |
| h | Help | This list plus safety notes. |
| 0 | Exit | Quit. |

## Breach check (free)

Menu **8** uses [XposedOrNot](https://xposedornot.com/api_doc). No API key and no signup. One email per check; lists are rejected. Rate limits are on their side (about 2/sec, 25/hour).

**Password Leak Check (menu 9)** uses Have I Been Pwned **Pwned Passwords** (k-anonymity). That endpoint is also free and needs no key. Only a 5-character hash prefix is sent.

## Safety (enforced in code)

- Shred, overwrite-scrub, history truncate, temp delete, clipboard clear, HKCU startup disable, and browser-data delete require an explicit `y` (default **No**) and print what will be affected.
- Paths under Windows, Program Files, other users' profiles, and the 66-Tool install directory are refused.
- Breach check accepts a single identifier typed for yourself; no batch/file loops.
- No scanning of other machines or ports.

### Windows notes

- PowerShell history is typically `%USERPROFILE%\AppData\Roaming\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt` (and the PowerShell 7 copy under `Documents\PowerShell\...`).
- User temp is `tempfile.gettempdir()` (usually `%LOCALAPPDATA%\Temp`). Files in use are skipped.
- Clipboard is emptied via the Windows clipboard API.

### Shredding on SSDs

Overwriting a file on an SSD (TRIM, wear leveling) is **best-effort**. It is not a guarantee against forensic recovery. Full-disk encryption is the stronger control.

## Out of scope

- Network / port scanning, packet sniffing, exploits, reverse shells
- Touching other users' files, system logs, or Event Viewer
- Looking up anyone else's email or username in HIBP
- Automating a browser for WebRTC or fingerprint collection

## Layout

```
OpsecPanel/
  main.py
  config.py
  ui.py
  safety.py
  config.example.yaml
  modules/          one file per tool
  wordlists/        EFF short wordlist (Diceware)
```
