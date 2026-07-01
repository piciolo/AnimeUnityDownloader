"""Reusable custom widgets: anime cards and download rows."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .models import Anime
from .net import AnimeUnityClient
from .workers import PosterWorker

CARD_WIDTH = 176
POSTER_W = 176
POSTER_H = 248


def human_size(num_bytes: float) -> str:
    """Return a human-readable size string."""
    if num_bytes < 0:
        return "?"
    step = 1024.0
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num_bytes < step:
            return f"{num_bytes:.0f} {unit}" if unit == "B" else f"{num_bytes:.1f} {unit}"
        num_bytes /= step
    return f"{num_bytes:.1f} PB"


def _badge(text: str, object_name: str = "Badge") -> QLabel:
    label = QLabel(text)
    label.setObjectName(object_name)
    label.setAlignment(Qt.AlignCenter)
    return label


class AnimeCard(QFrame):
    """A clickable poster card representing one anime."""

    # Shared in-memory pixmap cache (posters rarely change and repeat across tabs).
    _pixmap_cache: dict[str, QPixmap] = {}

    clicked = Signal(object)  # emits the Anime

    def __init__(self, anime: Anime, client: AnimeUnityClient, pool) -> None:
        super().__init__()
        self.anime = anime
        self._client = client
        self._pool = pool

        self.setObjectName("Card")
        self.setFixedWidth(CARD_WIDTH)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 10)
        layout.setSpacing(8)

        self.poster = QLabel()
        self.poster.setFixedSize(POSTER_W, POSTER_H)
        self.poster.setAlignment(Qt.AlignCenter)
        self.poster.setScaledContents(False)
        self.poster.setStyleSheet(
            "background:#15161f;border-radius:10px;color:#5b6079;font-size:32px;"
        )
        self.poster.setText("🎬")
        layout.addWidget(self.poster)

        title = QLabel(anime.title)
        title.setObjectName("CardTitle")
        title.setWordWrap(True)
        title.setFixedHeight(38)
        title.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(title)

        badges = QHBoxLayout()
        badges.setSpacing(5)
        if anime.anime_type:
            badges.addWidget(_badge(anime.anime_type))
        if anime.year:
            badges.addWidget(_badge(anime.year))
        if anime.dubbed:
            badges.addWidget(_badge("DUB", "BadgeDub"))
        badges.addStretch(1)
        layout.addLayout(badges)

        meta = QLabel(f"{anime.episodes_count} ep · ⭐ {anime.score or '–'}")
        meta.setObjectName("Muted")
        layout.addWidget(meta)

        self.setToolTip(anime.title)
        self._load_poster()

    def _load_poster(self) -> None:
        url = self.anime.poster
        if not url:
            return
        cached = self._pixmap_cache.get(url)
        if cached is not None:
            self._apply_pixmap(cached)
            return
        worker = PosterWorker(self._client, url)
        worker.signals.done.connect(self._on_poster_bytes)
        self._pool.start(worker)

    def _on_poster_bytes(self, url: str, data: bytes) -> None:
        pixmap = QPixmap()
        if not pixmap.loadFromData(data):
            return
        self._pixmap_cache[url] = pixmap
        self._apply_pixmap(pixmap)

    def _apply_pixmap(self, pixmap: QPixmap) -> None:
        scaled = pixmap.scaled(
            POSTER_W,
            POSTER_H,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )
        self.poster.setText("")
        self.poster.setPixmap(scaled)

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.anime)
        super().mousePressEvent(event)


class DownloadRow(QFrame):
    """A single row in the downloads panel, tracking one episode's progress."""

    cancel_requested = Signal(int)  # task_id
    remove_requested = Signal(int)  # task_id

    def __init__(self, task_id: int, title: str) -> None:
        super().__init__()
        self.task_id = task_id
        self._finished = False

        self.setObjectName("Row")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(14, 10, 12, 10)
        outer.setSpacing(12)

        left = QVBoxLayout()
        left.setSpacing(6)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-weight:600;")
        left.addWidget(self.title_label)

        bar_row = QHBoxLayout()
        bar_row.setSpacing(10)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(True)
        bar_row.addWidget(self.bar, 1)

        self.status_label = QLabel("In coda…")
        self.status_label.setObjectName("Muted")
        self.status_label.setMinimumWidth(190)
        self.status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        bar_row.addWidget(self.status_label)
        left.addLayout(bar_row)

        outer.addLayout(left, 1)

        self.action_button = QPushButton("Annulla")
        self.action_button.setObjectName("Danger")
        self.action_button.setFixedWidth(88)
        self.action_button.clicked.connect(self._on_action)
        outer.addWidget(self.action_button)

    def _on_action(self) -> None:
        if self._finished:
            self.remove_requested.emit(self.task_id)
        else:
            self.cancel_requested.emit(self.task_id)
            self.status_label.setText("Annullamento…")
            self.action_button.setEnabled(False)

    def set_status(self, text: str) -> None:
        if not self._finished:
            self.status_label.setText(text)

    def set_progress(self, downloaded: int, total: int, speed: float) -> None:
        if self._finished:
            return
        if total > 0:
            percent = int(downloaded / total * 100)
            self.bar.setRange(0, 100)
            self.bar.setValue(percent)
            self.status_label.setText(
                f"{human_size(downloaded)} / {human_size(total)}  ·  "
                f"{human_size(speed)}/s"
            )
        else:
            self.bar.setRange(0, 0)  # indeterminate
            self.status_label.setText(
                f"{human_size(downloaded)}  ·  {human_size(speed)}/s"
            )

    def set_finished(self, success: bool, message: str) -> None:
        self._finished = True
        self.bar.setRange(0, 100)
        self.action_button.setEnabled(True)
        self.action_button.setObjectName("Ghost")
        self.action_button.setText("Rimuovi")
        self.action_button.style().unpolish(self.action_button)
        self.action_button.style().polish(self.action_button)

        if success:
            self.bar.setValue(100)
            if message == "Già presente":
                self.status_label.setText("✓ Già presente")
            else:
                self.status_label.setText("✓ Completato")
            self.status_label.setStyleSheet("color:#3ecf8e;")
        elif message == "Annullato":
            self.status_label.setText("Annullato")
            self.status_label.setStyleSheet("color:#9aa0b4;")
        else:
            self.status_label.setText(message)
            self.status_label.setStyleSheet("color:#ff5c72;")
            self.status_label.setToolTip(message)
