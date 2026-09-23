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
