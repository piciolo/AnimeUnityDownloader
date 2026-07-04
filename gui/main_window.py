"""Main application window: search/browse, episode picker and download queue."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .flowlayout import FlowLayout
from .models import Anime, Episode
from .net import ORDER_OPTIONS, AnimeUnityClient, sanitize_name
from .settings import MAX_CONCURRENCY, AppSettings
from .theme import APP_QSS
from .widgets import AnimeCard, DownloadRow
from .workers import DownloadTask, EpisodesWorker, PosterWorker, SearchWorker

PAGE_SIZE = 30


def _clear_layout(layout) -> None:
    """Remove and delete every widget in a layout."""
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()


class MainWindow(QMainWindow):
    """Top-level window."""

    def __init__(self) -> None:
        super().__init__()
        self.settings = AppSettings()
        self.client = AnimeUnityClient(self.settings.base_url)

        self.io_pool = QThreadPool.globalInstance()
        self.io_pool.setMaxThreadCount(max(8, self.io_pool.maxThreadCount()))
        self.download_pool = QThreadPool()
        self.download_pool.setMaxThreadCount(self.settings.concurrency)

        # Query + task state
        self._search_token = 0
        self._append_next = False
        self._query: dict = {"title": "", "order": False, "dubbed": False, "offset": 0}
        self._detail_anime: Anime | None = None
        self._tasks: dict[int, DownloadTask] = {}
        self._rows: dict[int, DownloadRow] = {}
        self._task_counter = 0

        self.setWindowTitle("AnimeUnity Downloader")
        self.resize(1180, 820)
        self.setMinimumSize(940, 640)

        self._build_ui()
        # Land on something useful instead of a blank grid.
        self._browse("Popolarità")

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #
    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(22, 18, 22, 16)
        layout.setSpacing(14)

        layout.addLayout(self._build_header())

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_catalog_tab(), "Catalogo")
        self.tabs.addTab(self._build_downloads_tab(), "Download")
        layout.addWidget(self.tabs, 1)

        # Press Esc to go back from an anime detail to the results.
        QShortcut(QKeySequence(Qt.Key_Escape), self, activated=self._go_back)

    def _go_back(self) -> None:
        """Return from the anime detail view to the results grid."""
        if self.tabs.currentIndex() == 0 and self.catalog_stack.currentIndex() == 1:
            self.catalog_stack.setCurrentIndex(0)

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt override)
        # Support the mouse "back" button (side button) as a back action.
        if event.button() == Qt.BackButton:
            self._go_back()
            event.accept()
            return
        super().mousePressEvent(event)

    def _build_header(self) -> QVBoxLayout:
        box = QVBoxLayout()
        box.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel("AnimeUnity Downloader")
        title.setObjectName("Title")
        top.addWidget(title)
        top.addStretch(1)

        self.folder_button = QPushButton("📁  Cartella download")
        self.folder_button.setObjectName("Ghost")
        self.folder_button.clicked.connect(self._choose_folder)
        self.folder_button.setToolTip(self.settings.download_dir)
        top.addWidget(self.folder_button)
        box.addLayout(top)

        # Search row
        search_row = QHBoxLayout()
        search_row.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Cerca un anime…  (es. Naruto, One Piece)")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.returnPressed.connect(self._on_search_clicked)
        search_row.addWidget(self.search_input, 1)

        self.order_combo = QComboBox()
        for label in ORDER_OPTIONS:
            self.order_combo.addItem(label)
        search_row.addWidget(self.order_combo)

        self.dub_check = QCheckBox("Solo DUB (ITA)")
        search_row.addWidget(self.dub_check)

        search_button = QPushButton("Cerca")
        search_button.setObjectName("Primary")
        search_button.clicked.connect(self._on_search_clicked)
        search_row.addWidget(search_button)
        box.addLayout(search_row)

        # Quick browse chips
        chips = QHBoxLayout()
        chips.setSpacing(8)
        chips.addWidget(QLabel("Sfoglia:"))
        for label, order in (
            ("🔥 Popolari", "Popolarità"),
            ("👁 Più visti", "Visite"),
            ("⭐ Migliori", "Valutazione"),
        ):
            chip = QPushButton(label)
            chip.setObjectName("Ghost")
            chip.clicked.connect(lambda _=False, o=order: self._browse(o))
            chips.addWidget(chip)
        chips.addStretch(1)
        box.addLayout(chips)
        return box

    def _build_catalog_tab(self) -> QWidget:
        self.catalog_stack = QStackedWidget()
        self.catalog_stack.addWidget(self._build_results_page())
        self.catalog_stack.addWidget(self._build_detail_page())
        return self.catalog_stack

    def _build_results_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 6, 0, 0)
        layout.setSpacing(10)

        self.status_label = QLabel("")
        self.status_label.setObjectName("Muted")
        layout.addWidget(self.status_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self.grid = FlowLayout(container, margin=2, h_spacing=16, v_spacing=18)
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        self.load_more_button = QPushButton("Carica altri risultati")
        self.load_more_button.setObjectName("Ghost")
        self.load_more_button.clicked.connect(self._on_load_more)
        self.load_more_button.setVisible(False)
        layout.addWidget(self.load_more_button, 0, Qt.AlignCenter)
        return page

    def _build_detail_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 6, 0, 0)
        layout.setSpacing(14)

        back = QPushButton("←  Indietro")
        back.setObjectName("BackButton")
        back.setCursor(Qt.PointingHandCursor)
        back.setFixedHeight(38)
        back.setMinimumWidth(150)
        back.setToolTip("Torna ai risultati (Esc)")
        back.clicked.connect(self._go_back)
        back_row = QHBoxLayout()
        back_row.addWidget(back)
        back_row.addStretch(1)
        layout.addLayout(back_row)

        header = QHBoxLayout()
        header.setSpacing(18)

        self.detail_poster = QLabel()
        self.detail_poster.setFixedSize(180, 254)
        self.detail_poster.setAlignment(Qt.AlignCenter)
        self.detail_poster.setStyleSheet(
            "background:#15161f;border-radius:12px;color:#5b6079;font-size:34px;"
        )
        header.addWidget(self.detail_poster)

        info = QVBoxLayout()
        info.setSpacing(8)
        self.detail_title = QLabel("")
        self.detail_title.setObjectName("SectionTitle")
        self.detail_title.setWordWrap(True)
        info.addWidget(self.detail_title)

        self.detail_meta = QLabel("")
        self.detail_meta.setObjectName("Muted")
        info.addWidget(self.detail_meta)

        self.detail_plot = QLabel("")
        self.detail_plot.setWordWrap(True)
        self.detail_plot.setObjectName("Muted")
        self.detail_plot.setAlignment(Qt.AlignTop)
        info.addWidget(self.detail_plot, 1)
        header.addLayout(info, 1)
        layout.addLayout(header)

        # Selection controls
        controls = QHBoxLayout()
        controls.setSpacing(8)
        select_all = QPushButton("Seleziona tutti")
        select_all.setObjectName("Ghost")
        select_all.clicked.connect(lambda: self._set_all_episodes(checked=True))
        clear_all = QPushButton("Deseleziona")
        clear_all.setObjectName("Ghost")
        clear_all.clicked.connect(lambda: self._set_all_episodes(checked=False))
        controls.addWidget(select_all)
        controls.addWidget(clear_all)

        controls.addSpacing(16)
        controls.addWidget(QLabel("Dal"))
        self.range_from = QSpinBox()
        self.range_from.setMinimum(1)
        controls.addWidget(self.range_from)
        controls.addWidget(QLabel("al"))
        self.range_to = QSpinBox()
        self.range_to.setMinimum(1)
        controls.addWidget(self.range_to)
        apply_range = QPushButton("Seleziona intervallo")
        apply_range.setObjectName("Ghost")
        apply_range.clicked.connect(self._select_range)
        controls.addWidget(apply_range)
        controls.addStretch(1)
        layout.addLayout(controls)

        self.episode_list = QListWidget()
        self.episode_list.setUniformItemSizes(True)
        layout.addWidget(self.episode_list, 1)

        bottom = QHBoxLayout()
        self.episodes_status = QLabel("")
        self.episodes_status.setObjectName("Muted")
        bottom.addWidget(self.episodes_status)
        bottom.addStretch(1)
        self.download_button = QPushButton("⬇  Scarica selezionati")
        self.download_button.setObjectName("Primary")
        self.download_button.clicked.connect(self._download_selected)
        bottom.addWidget(self.download_button)
        layout.addLayout(bottom)
        return page

    def _build_downloads_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(12)

        bar = QHBoxLayout()
        self.folder_label = QLabel()
        self.folder_label.setObjectName("Muted")
        self._refresh_folder_label()
        bar.addWidget(self.folder_label, 1)

        bar.addWidget(QLabel("Simultanei:"))
        self.concurrency_spin = QSpinBox()
        self.concurrency_spin.setRange(1, MAX_CONCURRENCY)
        self.concurrency_spin.setValue(self.settings.concurrency)
        self.concurrency_spin.valueChanged.connect(self._on_concurrency_changed)
        bar.addWidget(self.concurrency_spin)

        clear_done = QPushButton("Pulisci completati")
        clear_done.setObjectName("Ghost")
        clear_done.clicked.connect(self._clear_finished)
        bar.addWidget(clear_done)
        layout.addLayout(bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self.queue_layout = QVBoxLayout(container)
        self.queue_layout.setContentsMargins(2, 2, 2, 2)
        self.queue_layout.setSpacing(10)
        self.queue_layout.addStretch(1)
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        self.empty_queue_label = QLabel(
            "Nessun download. Cerca un anime, apri la scheda e scegli gli episodi."
        )
        self.empty_queue_label.setObjectName("Muted")
        self.empty_queue_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.empty_queue_label)
        return page

    # ------------------------------------------------------------------ #
    # Search / browse
    # ------------------------------------------------------------------ #
    def _on_search_clicked(self) -> None:
        title = self.search_input.text().strip()
        order = ORDER_OPTIONS[self.order_combo.currentText()]
        self._start_query(title=title, order=order, dubbed=self.dub_check.isChecked())

    def _browse(self, order_value: str) -> None:
        self.search_input.clear()
        # Reflect the browse order in the combo if present.
        for label, value in ORDER_OPTIONS.items():
            if value == order_value:
                self.order_combo.setCurrentText(label)
                break
        self._start_query(title="", order=order_value, dubbed=self.dub_check.isChecked())

    def _start_query(self, *, title: str, order, dubbed: bool) -> None:
        self.catalog_stack.setCurrentIndex(0)
        self._search_token += 1
        self._append_next = False
        self._query = {"title": title, "order": order, "dubbed": dubbed, "offset": 0}
        _clear_layout(self.grid)
        self.load_more_button.setVisible(False)
        self.status_label.setText("Caricamento…")
        self._spawn_search()

    def _on_load_more(self) -> None:
        self._append_next = True
        self.load_more_button.setEnabled(False)
        self.load_more_button.setText("Caricamento…")
        self._spawn_search()

    def _spawn_search(self) -> None:
        worker = SearchWorker(
            self.client,
            self._search_token,
            title=self._query["title"] or None,
            order=self._query["order"],
            offset=self._query["offset"],
            dubbed=self._query["dubbed"],
        )
        worker.signals.results.connect(self._on_search_results)
        worker.signals.error.connect(self._on_search_error)
        self.io_pool.start(worker)

    def _on_search_results(self, token: object, animes: list) -> None:
        if token != self._search_token:
            return  # stale response from a superseded query
        if not self._append_next and not animes:
            self.status_label.setText("Nessun risultato trovato.")
            self.load_more_button.setVisible(False)
            return

        for anime in animes:
            card = AnimeCard(anime, self.client, self.io_pool)
            card.clicked.connect(self._open_detail)
            self.grid.addWidget(card)

        self._query["offset"] += len(animes)
        self._append_next = False
        self.status_label.setText(f"{self._query['offset']} risultati")

        has_more = len(animes) >= PAGE_SIZE
        self.load_more_button.setVisible(has_more)
        self.load_more_button.setEnabled(True)
        self.load_more_button.setText("Carica altri risultati")

    def _on_search_error(self, token: object, message: str) -> None:
        if token != self._search_token:
            return
        self.status_label.setText(f"Errore di rete: {message}")
        self.load_more_button.setEnabled(True)
        self.load_more_button.setText("Carica altri risultati")

    # ------------------------------------------------------------------ #
    # Detail / episodes
    # ------------------------------------------------------------------ #
    def _open_detail(self, anime: Anime) -> None:
        self._detail_anime = anime
        self.catalog_stack.setCurrentIndex(1)
        self.detail_title.setText(anime.title)
        meta_bits = [
            bit
            for bit in (
                anime.anime_type,
                anime.year,
                f"{anime.episodes_count} episodi",
                f"⭐ {anime.score}" if anime.score else "",
                "DUB ITA" if anime.dubbed else "SUB ITA",
                anime.status,
            )
            if bit
        ]
        self.detail_meta.setText("   ·   ".join(meta_bits))
        plot = anime.plot or ""
        self.detail_plot.setText(plot[:600] + ("…" if len(plot) > 600 else ""))

        self._load_detail_poster(anime.poster)

        self.episode_list.clear()
        self.episodes_status.setText("Caricamento episodi…")
        self.download_button.setEnabled(False)

        count = max(anime.episodes_count, 1)
        self.range_from.setMaximum(count)
        self.range_to.setMaximum(count)
        self.range_from.setValue(1)
        self.range_to.setValue(count)

        worker = EpisodesWorker(self.client, anime)
        worker.signals.results.connect(self._on_episodes_results)
        worker.signals.error.connect(self._on_episodes_error)
        self.io_pool.start(worker)

    def _load_detail_poster(self, url: str) -> None:
        self.detail_poster.setText("🎬")
        self.detail_poster.setPixmap(QPixmap())
        if not url:
            return
        cached = AnimeCard._pixmap_cache.get(url)
        if cached is not None:
            self._apply_detail_poster(url, cached)
            return
        worker = PosterWorker(self.client, url)
        worker.signals.done.connect(self._on_detail_poster_bytes)
        self.io_pool.start(worker)

    def _on_detail_poster_bytes(self, url: str, data: bytes) -> None:
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            AnimeCard._pixmap_cache[url] = pixmap
            self._apply_detail_poster(url, pixmap)

    def _apply_detail_poster(self, url: str, pixmap: QPixmap) -> None:
        # Only apply if the user is still looking at this anime.
        if self._detail_anime and self._detail_anime.poster == url:
            self.detail_poster.setText("")
            self.detail_poster.setPixmap(
                pixmap.scaled(
                    180, 254, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
                )
            )

    def _on_episodes_results(self, api_id: object, episodes: list) -> None:
        if not self._detail_anime or api_id != self._detail_anime.api_id:
            return
        self.episode_list.clear()
        for episode in episodes:
            item = QListWidgetItem(episode.number_label)
            item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, episode)
            self.episode_list.addItem(item)
        self.episodes_status.setText(f"{len(episodes)} episodi disponibili")
        self.download_button.setEnabled(bool(episodes))

    def _on_episodes_error(self, api_id: object, message: str) -> None:
        if not self._detail_anime or api_id != self._detail_anime.api_id:
            return
        self.episodes_status.setText(f"Errore nel caricamento episodi: {message}")

    def _set_all_episodes(self, *, checked: bool) -> None:
        state = Qt.Checked if checked else Qt.Unchecked
        for i in range(self.episode_list.count()):
            self.episode_list.item(i).setCheckState(state)

    def _select_range(self) -> None:
        low = self.range_from.value()
        high = self.range_to.value()
        if low > high:
            low, high = high, low
        for i in range(self.episode_list.count()):
            item = self.episode_list.item(i)
            episode: Episode = item.data(Qt.UserRole)
            value = episode.number_value
            in_range = value is not None and low <= value <= high
            item.setCheckState(Qt.Checked if in_range else Qt.Unchecked)

    def _checked_episodes(self) -> list[Episode]:
        result = []
        for i in range(self.episode_list.count()):
            item = self.episode_list.item(i)
            if item.checkState() == Qt.Checked:
                result.append(item.data(Qt.UserRole))
        return result

    # ------------------------------------------------------------------ #
    # Downloads
    # ------------------------------------------------------------------ #
    def _download_selected(self) -> None:
        if not self._detail_anime:
            return
        episodes = self._checked_episodes()
        if not episodes:
            QMessageBox.information(
                self, "Nessun episodio", "Seleziona almeno un episodio da scaricare."
            )
            return

        anime = self._detail_anime
        dest_dir = Path(self.settings.download_dir) / sanitize_name(anime.title)

        for episode in episodes:
            self._enqueue_download(anime.title, episode, dest_dir)

        self.tabs.setCurrentIndex(1)
        self._update_empty_queue()

    def _enqueue_download(self, anime_title: str, episode: Episode, dest_dir: Path) -> None:
        self._task_counter += 1
        task_id = self._task_counter
        row = DownloadRow(task_id, f"{anime_title}  ·  {episode.number_label}")
        row.cancel_requested.connect(self._cancel_task)
        row.remove_requested.connect(self._remove_task)
        # Insert above the trailing stretch.
        self.queue_layout.insertWidget(self.queue_layout.count() - 1, row)
        self._rows[task_id] = row

        task = DownloadTask(self.client, task_id, anime_title, episode, dest_dir)
        task.signals.progress.connect(self._on_task_progress)
        task.signals.status.connect(self._on_task_status)
        task.signals.finished.connect(self._on_task_finished)
        self._tasks[task_id] = task
        self.download_pool.start(task)

    def _on_task_progress(self, task_id: int, downloaded: int, total: int, speed: float) -> None:
        row = self._rows.get(task_id)
        if row:
            row.set_progress(downloaded, total, speed)

    def _on_task_status(self, task_id: int, text: str) -> None:
        row = self._rows.get(task_id)
        if row:
            row.set_status(text)

    def _on_task_finished(self, task_id: int, success: bool, message: str) -> None:
        row = self._rows.get(task_id)
        if row:
            row.set_finished(success, message)
        self._tasks.pop(task_id, None)
        self._update_empty_queue()

    def _cancel_task(self, task_id: int) -> None:
        task = self._tasks.get(task_id)
        if task:
            task.cancel()

    def _remove_task(self, task_id: int) -> None:
        row = self._rows.pop(task_id, None)
        if row:
            row.deleteLater()
        self._tasks.pop(task_id, None)
        self._update_empty_queue()

    def _clear_finished(self) -> None:
        for task_id, row in list(self._rows.items()):
            if task_id not in self._tasks:  # finished tasks are removed from _tasks
                self._rows.pop(task_id, None)
                row.deleteLater()
        self._update_empty_queue()

    def _update_empty_queue(self) -> None:
        self.empty_queue_label.setVisible(not self._rows)
        active = len(self._tasks)
        self.tabs.setTabText(1, f"Download ({active})" if active else "Download")

    # ------------------------------------------------------------------ #
    # Settings
    # ------------------------------------------------------------------ #
    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Scegli la cartella di download", self.settings.download_dir
        )
        if folder:
            self.settings.download_dir = folder
            self.folder_button.setToolTip(folder)
            self._refresh_folder_label()

    def _refresh_folder_label(self) -> None:
        if hasattr(self, "folder_label"):
            self.folder_label.setText(f"Cartella:  {self.settings.download_dir}")

    def _on_concurrency_changed(self, value: int) -> None:
        self.settings.concurrency = value
        self.download_pool.setMaxThreadCount(value)

    # ------------------------------------------------------------------ #
    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        # Cancel in-flight downloads (this also closes their live streams), then give
        # the pool a bounded moment to unwind before closing the shared HTTP client.
        for task in self._tasks.values():
            task.cancel()
        self.download_pool.clear()  # drop queued-but-not-started tasks
        self.download_pool.waitForDone(3000)
        self.client.close()
        super().closeEvent(event)


def create_window() -> MainWindow:
    """Create and return the main window (style applied by the caller)."""
    window = MainWindow()
    window.setStyleSheet(APP_QSS)
    return window
