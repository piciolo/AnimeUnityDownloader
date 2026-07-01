"""Build a standalone Windows executable with PyInstaller.

Run once:  ``python build_exe.py``
Result:    ``dist/AnimeUnity Downloader.exe`` (double-clickable, no console).
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).resolve().parent
APP_NAME = "AnimeUnity Downloader"


def main() -> None:
    logo = ROOT / "assets" / "logo.png"
    sep = ";" if sys.platform.startswith("win") else ":"

    args = [
        str(ROOT / "app.py"),
        "--name",
        APP_NAME,
        "--noconfirm",
        "--clean",
        "--windowed",          # no console window
        "--onefile",           # single .exe
        "--collect-submodules",
        "gui",
        # Anchor all output to the project root regardless of the current directory.
        "--distpath",
        str(ROOT / "dist"),
        "--workpath",
        str(ROOT / "build"),
        "--specpath",
        str(ROOT),
    ]

    # Bundle the logo so the app can show its icon at runtime.
    if logo.exists():
        args += ["--add-data", f"{logo}{sep}assets"]
        # A .ico is required for the exe icon; skip if only a .png is present.
        ico = ROOT / "assets" / "logo.ico"
        if ico.exists():
            args += ["--icon", str(ico)]

    PyInstaller.__main__.run(args)

    exe = ROOT / "dist" / f"{APP_NAME}.exe"
    if exe.exists():
        print(f"\n[OK] Eseguibile creato: {exe}")
    else:
        print("\n[!] Build terminata ma l'eseguibile non e' stato trovato.")


if __name__ == "__main__":
    main()
