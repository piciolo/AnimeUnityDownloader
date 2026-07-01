"""Persistent user settings backed by ``QSettings``.

Stores the download folder, the number of concurrent downloads and the site base URL
so the user's choices survive across launches.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings

from .net import DEFAULT_BASE_URL

_ORG = "AnimeUnityDownloader"
_APP = "GUI"

DEFAULT_CONCURRENCY = 3
MAX_CONCURRENCY = 6


def _default_download_dir() -> str:
    return str(Path.home() / "Downloads" / "AnimeUnity")


class AppSettings:
    """Thin, typed wrapper around ``QSettings``."""

    def __init__(self) -> None:
        self._settings = QSettings(_ORG, _APP)

    @property
    def download_dir(self) -> str:
        return str(self._settings.value("download_dir", _default_download_dir()))

    @download_dir.setter
    def download_dir(self, value: str) -> None:
        self._settings.setValue("download_dir", value)

    @property
    def concurrency(self) -> int:
        value = int(self._settings.value("concurrency", DEFAULT_CONCURRENCY))
        return max(1, min(value, MAX_CONCURRENCY))

    @concurrency.setter
    def concurrency(self, value: int) -> None:
        self._settings.setValue("concurrency", int(value))

    @property
    def base_url(self) -> str:
        return str(self._settings.value("base_url", DEFAULT_BASE_URL))

    @base_url.setter
    def base_url(self, value: str) -> None:
        self._settings.setValue("base_url", value)
