"""Background workers (``QRunnable``) that keep the UI responsive.

Every network call runs on a Qt thread pool and reports back through signals, so the
main thread only ever touches ready-to-display data.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal

from .models import Anime, Episode
from .net import AnimeUnityClient, DownloadCancelled, build_filename


class SearchSignals(QObject):
    results = Signal(object, list)  # query_token, list[Anime]
    error = Signal(object, str)


class SearchWorker(QRunnable):
    """Run a search/browse query off the UI thread."""

    def __init__(
        self,
        client: AnimeUnityClient,
        token: object,
        *,
        title: str | None,
        order: str | bool,
        offset: int,
        dubbed: bool,
    ) -> None:
        super().__init__()
        self.client = client
        self.token = token
        self.title = title
        self.order = order
        self.offset = offset
        self.dubbed = dubbed
        self.signals = SearchSignals()

    def run(self) -> None:
        try:
            records = self.client.search(
                self.title,
                order=self.order,
                offset=self.offset,
                dubbed=self.dubbed,
            )
            animes = [Anime.from_record(record) for record in records]
            self.signals.results.emit(self.token, animes)
        except Exception as exc:  # noqa: BLE001 - surfaced to the user
            self.signals.error.emit(self.token, str(exc))


class EpisodesSignals(QObject):
    results = Signal(object, list)  # anime_api_id, list[Episode]
    error = Signal(object, str)


class EpisodesWorker(QRunnable):
    """Fetch the full episode list for an anime."""

    def __init__(self, client: AnimeUnityClient, anime: Anime) -> None:
        super().__init__()
        self.client = client
        self.anime = anime
        self.signals = EpisodesSignals()

    def run(self) -> None:
        try:
            records = self.client.get_episodes(
                self.anime.api_id, self.anime.episodes_count
            )
            episodes = [Episode.from_record(record) for record in records]
            self.signals.results.emit(self.anime.api_id, episodes)
        except Exception as exc:  # noqa: BLE001
            self.signals.error.emit(self.anime.api_id, str(exc))


class PosterSignals(QObject):
    done = Signal(str, bytes)  # url, image bytes
    error = Signal(str)


class PosterWorker(QRunnable):
    """Download a poster image."""

    def __init__(self, client: AnimeUnityClient, url: str) -> None:
        super().__init__()
        self.client = client
        self.url = url
        self.signals = PosterSignals()

    def run(self) -> None:
        try:
            data = self.client.fetch_bytes(self.url)
            self.signals.done.emit(self.url, data)
        except Exception:  # noqa: BLE001 - a missing poster is non-fatal
            self.signals.error.emit(self.url)


class DownloadSignals(QObject):
    # task_id, downloaded_bytes, total_bytes, speed_bytes_per_sec
    progress = Signal(int, int, int, float)
    status = Signal(int, str)               # task_id, status text
    finished = Signal(int, bool, str)       # task_id, success, message


class DownloadTask(QRunnable):
    """Resolve an episode's direct link and stream it to disk with progress."""

    def __init__(
        self,
        client: AnimeUnityClient,
        task_id: int,
        anime_title: str,
        episode: Episode,
        dest_dir: Path,
    ) -> None:
        super().__init__()
        self.client = client
        self.task_id = task_id
        self.anime_title = anime_title
        self.episode = episode
        self.dest_dir = dest_dir
        self.signals = DownloadSignals()
        self._cancel = threading.Event()
        self._response = None
        self._last_emit = 0.0
        self._start_time = 0.0

    def cancel(self) -> None:
        self._cancel.set()
        # Close the live stream (if any) so a blocked read unblocks immediately
        # instead of waiting for the read timeout.
        response = self._response
        if response is not None:
            try:
                response.close()
            except Exception:  # noqa: BLE001 - best-effort interruption
                pass

    @property
    def cancelled(self) -> bool:
        return self._cancel.is_set()

    def _set_response(self, response) -> None:
        self._response = response

    def _on_progress(self, downloaded: int, total: int) -> None:
        now = time.monotonic()
        # Throttle UI updates to ~12 per second. Always emit the final chunk, but only
        # when the total is known (otherwise the guard must still throttle).
        is_final = total > 0 and downloaded >= total
        if now - self._last_emit < 0.08 and not is_final:
            return
        self._last_emit = now
        elapsed = max(now - self._start_time, 1e-6)
        speed = downloaded / elapsed
        self.signals.progress.emit(self.task_id, downloaded, total, speed)

    def run(self) -> None:
        if self._cancel.is_set():
            self.signals.finished.emit(self.task_id, False, "Annullato")
            return
        try:
            self.signals.status.emit(self.task_id, "Risoluzione link…")
            download_url = self.client.resolve_download_url(self.episode.id)

            filename = build_filename(self.anime_title, self.episode, download_url)
            dest_path = self.dest_dir / filename

            if dest_path.exists():
                self.signals.finished.emit(self.task_id, True, "Già presente")
                return

            self.signals.status.emit(self.task_id, "Download…")
            self._start_time = time.monotonic()
            self.client.download_file(
                download_url,
                dest_path,
                progress=self._on_progress,
                should_cancel=self._cancel.is_set,
                on_response=self._set_response,
            )
            self.signals.finished.emit(self.task_id, True, str(dest_path))
        except DownloadCancelled:
            self.signals.finished.emit(self.task_id, False, "Annullato")
        except Exception as exc:  # noqa: BLE001
            # Closing the stream to cancel surfaces as a read/stream error here.
            if self._cancel.is_set():
                self.signals.finished.emit(self.task_id, False, "Annullato")
            else:
                self.signals.finished.emit(self.task_id, False, f"Errore: {exc}")
