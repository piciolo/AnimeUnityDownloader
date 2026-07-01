"""Entry point for the AnimeUnity Downloader desktop application.

Double-click the packaged executable (or run ``python app.py``) to open the GUI.
No command-line arguments are required.
"""

from __future__ import annotations

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from gui.main_window import create_window
from gui.theme import APP_QSS


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("AnimeUnity Downloader")
    app.setOrganizationName("AnimeUnityDownloader")
    app.setStyle("Fusion")
    app.setStyleSheet(APP_QSS)

    # Use the bundled logo as the window/taskbar icon when available.
    from pathlib import Path

    logo = Path(__file__).resolve().parent / "assets" / "logo.png"
    if logo.exists():
        app.setWindowIcon(QIcon(str(logo)))

    window = create_window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
