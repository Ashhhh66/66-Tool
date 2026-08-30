"""Small window with a Launch button that opens the 66-Tool CMD panel."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def console_python() -> str:
    venv = ROOT / ".venv" / "Scripts" / "python.exe"
    if venv.is_file():
        return str(venv)
    exe = Path(sys.executable)
    if exe.name.lower() == "pythonw.exe":
        sibling = exe.with_name("python.exe")
        if sibling.is_file():
            return str(sibling)
    return str(exe)


def launch_panel() -> None:
    py = console_python()
    main = ROOT / "main.py"
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NEW_CONSOLE
    subprocess.Popen([py, str(main)], cwd=str(ROOT), creationflags=flags)


def add_desktop_shortcut() -> Path:
    desktop = Path.home() / "Desktop"
    if not desktop.is_dir():
        desktop = Path.home() / "OneDrive" / "Desktop"
    if not desktop.is_dir():
        raise FileNotFoundError("Could not find your Desktop folder.")
    script = ROOT / "install-shortcut.ps1"
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
        ],
        check=True,
        cwd=str(ROOT),
    )
    return desktop / "66 Tool.lnk"


def main() -> None:
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.title("66 TOOL")
    root.configure(bg="#071018")
    root.resizable(False, False)
    root.geometry("420x340")

    frame = tk.Frame(root, bg="#071018", padx=28, pady=24)
    frame.pack(fill="both", expand=True)

    tk.Label(
        frame,
        text="66 TOOL",
        fg="#7ee0ff",
        bg="#071018",
        font=("Segoe UI", 28, "bold"),
    ).pack(pady=(8, 0))
    tk.Label(
        frame,
        text="ASHH66  ·  privacy hygiene",
        fg="#8aa0b4",
        bg="#071018",
        font=("Segoe UI", 11),
    ).pack(pady=(0, 22))

    btn = tk.Button(
        frame,
        text="Open CMD panel",
        command=launch_panel,
        bg="#12b5c9",
        fg="#041018",
        activebackground="#7ee0ff",
        activeforeground="#041018",
        font=("Segoe UI", 14, "bold"),
        relief="flat",
        padx=18,
        pady=14,
        cursor="hand2",
    )
    btn.pack(fill="x")

    def on_shortcut() -> None:
        try:
            path = add_desktop_shortcut()
            messagebox.showinfo("66 TOOL", f"Shortcut ready:\n{path}\n\nYou can pin it to the taskbar.")
        except Exception as exc:
            messagebox.showerror("66 TOOL", str(exc))

    link = tk.Button(
        frame,
        text="Add Desktop shortcut",
        command=on_shortcut,
        bg="#071018",
        fg="#7ee0ff",
        activebackground="#0c1a24",
        activeforeground="#ffffff",
        font=("Segoe UI", 10, "underline"),
        relief="flat",
        cursor="hand2",
    )
    link.pack(pady=(18, 0))

    tk.Label(
        frame,
        text="Opens the numbered menu in a Command Prompt window.",
        fg="#5c7184",
        bg="#071018",
        font=("Segoe UI", 9),
        wraplength=360,
    ).pack(pady=(16, 0))

    root.mainloop()


if __name__ == "__main__":
    main()
