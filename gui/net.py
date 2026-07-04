"""Networking / scraping layer for the GUI.

This mirrors the proven flow of the original command-line engine (same endpoints,
same ``window.downloadUrl`` extraction) but is synchronous and thread-safe so it can
be driven from Qt worker threads. It is intentionally self-contained (no imports from
``src``) so the GUI packages cleanly into a standalone executable.
"""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, unquote, urlparse

import httpx

# Status codes that indicate the CSRF token / session has gone stale.
_STALE_TOKEN_CODES = {403, 419}

# Recognises a resolution token such as "1080p" or "720p".
_QUALITY_PATTERN = re.compile(r"^\d{3,4}p$", re.IGNORECASE)

DEFAULT_BASE_URL = "https://www.animeunity.so"

# Regex used to pull the direct download link out of the video page scripts.
DOWNLOAD_LINK_PATTERN = re.compile(r"window\.downloadUrl\s*=\s*'(https?://[^\s']+)'")
CSRF_META_PATTERN = re.compile(r'name="csrf-token"\s+content="([^"]+)"')

# The API paginates episodes; this is the maximum window it accepts per request.
EPISODE_BATCH_SIZE = 120

# Ordering values accepted by the archive endpoint, mapped to friendly labels.
ORDER_OPTIONS: dict[str, str | bool] = {
    "Rilevanza": False,
    "Popolarità": "Popolarità",
    "Più visti": "Visite",
    "Valutazione": "Valutazione",
}

_FIREFOX_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) "
    "Gecko/20100101 Firefox/121.0"
)

_HTML_HEADERS = {
    "User-Agent": _FIREFOX_UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
}


def sanitize_name(name: str) -> str:
    """Replace characters that are invalid in Windows file/dir names."""
    cleaned = re.sub(r'[\\/:*?"<>|]', "_", name).strip().strip(".")
    return cleaned or "AnimeUnity"


class DownloadCancelled(Exception):
    """Raised internally when a download is cancelled by the user."""


class AnimeUnityClient:
    """Synchronous, thread-safe client for the AnimeUnity website.

    A single instance is shared across worker threads. ``httpx.Client`` is safe for
    concurrent requests; only the lazy CSRF-token bootstrap is guarded by a lock.
    """

    def __init__(self, base_url: str = DEFAULT_BASE_URL) -> None:
        self.base_url = base_url.rstrip("/")
        self.host = urlparse(self.base_url).netloc
        self._client = httpx.Client(
            headers=_HTML_HEADERS,
            timeout=30.0,
            follow_redirects=True,
            verify=False,  # noqa: S501 - matches the original engine; cert varies by mirror
            limits=httpx.Limits(max_connections=32, max_keepalive_connections=16),
        )
        self._csrf_token: str | None = None
        self._token_lock = threading.Lock()

    # ------------------------------------------------------------------ #
    # Session / token handling
    # ------------------------------------------------------------------ #
    def _ensure_token(self) -> str:
        """Fetch and cache the CSRF token (and session cookies) once."""
        if self._csrf_token:
            return self._csrf_token

        with self._token_lock:
            if self._csrf_token:  # re-check inside the lock
                return self._csrf_token
            response = self._client.get(f"{self.base_url}/archivio")
            response.raise_for_status()
            match = CSRF_META_PATTERN.search(response.text)
            if not match:
                message = "Impossibile ottenere il token CSRF da AnimeUnity."
                raise RuntimeError(message)
            self._csrf_token = match.group(1)
            return self._csrf_token

    def _api_headers(self) -> dict[str, str]:
        """Build headers for the JSON archive endpoint, including CSRF tokens."""
        token = self._ensure_token()
        headers = {
            "User-Agent": _FIREFOX_UA,
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json;charset=UTF-8",
            "X-CSRF-TOKEN": token,
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.base_url}/archivio",
            "Origin": self.base_url,
        }
        xsrf = self._client.cookies.get("XSRF-TOKEN")
        if xsrf:
            headers["X-XSRF-TOKEN"] = unquote(xsrf)
        return headers

    # ------------------------------------------------------------------ #
    # Search / browse
    # ------------------------------------------------------------------ #
    def search(
        self,
        title: str | None = None,
        *,
        order: str | bool = False,
        offset: int = 0,
        dubbed: bool = False,
    ) -> list[dict]:
        """Query the archive endpoint and return the raw records list.

        ``title`` empty/None with an ``order`` acts as a catalogue browse.
        """
        body = {
            "title": title if title else False,
            "type": False,
            "year": False,
            "order": order,
            "status": False,
            "genres": False,
            "offset": offset,
            "dubbed": 1 if dubbed else False,
            "season": False,
        }
        payload = self._post_archive(body)
        records = payload.get("records", payload if isinstance(payload, list) else [])
        return records or []

    def _post_archive(self, body: dict, *, retry: bool = True) -> dict:
        """POST to the archive endpoint, re-bootstrapping a stale CSRF token once."""
        response = self._client.post(
            f"{self.base_url}/archivio/get-animes",
            headers=self._api_headers(),
            content=json.dumps(body),
        )
        if response.status_code in _STALE_TOKEN_CODES and retry:
            # The cached token/session likely expired: drop it and try again with a
            # freshly fetched one (the next _api_headers() call re-bootstraps).
            with self._token_lock:
                self._csrf_token = None
            return self._post_archive(body, retry=False)

        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------ #
    # Episodes
    # ------------------------------------------------------------------ #
    def get_episodes(self, api_id: str, episodes_count: int) -> list[dict]:
        """Return every episode record for the given ``id-slug``.

        The endpoint only returns up to ``EPISODE_BATCH_SIZE`` episodes per call, so
        long series are fetched in successive ranges.
        """
        api_url = f"{self.base_url}/info_api/{api_id}"
        total = max(episodes_count, 1)
        all_episodes: list[dict] = []

        for start in range(1, total + 1, EPISODE_BATCH_SIZE):
            end = min(start + EPISODE_BATCH_SIZE - 1, total)
            response = self._client.get(
                f"{api_url}/0",
                params={"start_range": start, "end_range": end},
                headers={"User-Agent": _FIREFOX_UA, "X-Requested-With": "XMLHttpRequest"},
            )
            response.raise_for_status()
            all_episodes.extend(response.json().get("episodes", []))

        return all_episodes

    # ------------------------------------------------------------------ #
    # Download-link resolution
    # ------------------------------------------------------------------ #
    def resolve_download_url(self, episode_id: int) -> str:
        """Turn an episode id into a direct ``.mp4`` download URL."""
        embed = self._client.get(f"{self.base_url}/embed-url/{episode_id}")
        embed.raise_for_status()
        video_page_url = embed.text.strip()
        if not video_page_url.startswith("http"):
            message = f"Embed URL non valido per l'episodio {episode_id}."
            raise RuntimeError(message)

        page = self._client.get(video_page_url)
        page.raise_for_status()
        match = DOWNLOAD_LINK_PATTERN.search(page.text)
        if not match:
            message = f"Link di download non trovato per l'episodio {episode_id}."
            raise RuntimeError(message)
        return match.group(1)

    # ------------------------------------------------------------------ #
    # Binary fetches (posters + episode files)
    # ------------------------------------------------------------------ #
    def fetch_bytes(self, url: str) -> bytes:
        """Fetch a small binary resource (used for poster images)."""
        response = self._client.get(url, headers={"User-Agent": _FIREFOX_UA})
        response.raise_for_status()
        return response.content

    def download_file(
        self,
        url: str,
        dest_path: Path,
        *,
        progress: Callable[[int, int], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
        on_response: Callable[[object], None] | None = None,
    ) -> None:
        """Stream a file to ``dest_path`` while reporting progress, resuming if possible.

        If a ``.part`` file from a previous interrupted attempt exists, the download
        resumes from where it stopped via an HTTP ``Range`` request (falling back to a
        clean restart if the server ignores it). ``progress`` receives
        ``(downloaded_bytes, total_bytes)`` where ``downloaded_bytes`` is cumulative
        (including already-present bytes) and ``total_bytes`` is ``-1`` when unknown.

        On cancellation (:class:`DownloadCancelled`) or error the ``.part`` file is
        **kept** so the next attempt can resume it. ``on_response`` receives the live
        streaming response so the caller can close it to interrupt a stalled read.
        """
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = dest_path.with_suffix(dest_path.suffix + ".part")
        timeout = httpx.Timeout(connect=15.0, read=20.0, write=20.0, pool=15.0)

        # Two passes at most: the second only happens if a stale partial forced a clean
        # restart (HTTP 416 Range Not Satisfiable).
        for allow_restart in (True, False):
            existing = tmp_path.stat().st_size if tmp_path.exists() else 0
            headers = {"User-Agent": _FIREFOX_UA}
            if existing > 0:
                headers["Range"] = f"bytes={existing}-"

            with self._client.stream(
                "GET", url, headers=headers, timeout=timeout,
            ) as response:
                if on_response is not None:
                    on_response(response)

                if response.status_code == 416 and existing > 0 and allow_restart:
                    # Our partial is stale / already >= the file size: discard & restart.
                    tmp_path.unlink(missing_ok=True)
                    continue

                response.raise_for_status()

                resuming = existing > 0 and response.status_code == 206
                if resuming:
                    total = _content_range_total(response.headers)
                    if total is None:
                        remaining = _to_int(response.headers.get("Content-Length"))
                        total = existing + remaining if remaining is not None else -1
                    mode, downloaded = "ab", existing
                else:
                    total = _to_int(response.headers.get("Content-Length"), -1)
                    mode, downloaded = "wb", 0

                with tmp_path.open(mode) as handle:
                    for chunk in response.iter_bytes(chunk_size=1024 * 256):
                        if should_cancel and should_cancel():
                            raise DownloadCancelled
                        if not chunk:
                            continue
                        handle.write(chunk)
                        downloaded += len(chunk)
                        if progress:
                            progress(downloaded, total)
            break

        tmp_path.replace(dest_path)

    # ------------------------------------------------------------------ #
    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()


def _to_int(value: object, default: int | None = None) -> int | None:
    """Parse an int, returning ``default`` on any failure."""
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _content_range_total(headers: object) -> int | None:
    """Extract the total size from a ``Content-Range: bytes a-b/total`` header."""
    content_range = headers.get("Content-Range", "") if headers else ""
    if "/" in content_range:
        return _to_int(content_range.rsplit("/", 1)[-1].strip())
    return None


def episode_label(episode: "object") -> str:
    """Return the episode label used in filenames (zero-padded, or ``idN`` fallback)."""
    number = getattr(episode, "number", "") or ""
    if number.isdigit():
        return f"{int(number):02d}"
    if number:
        return number
    return f"id{getattr(episode, 'id', '')}"


def build_filename(anime_title: str, episode: "object", download_url: str) -> str:
    """Build a clean, readable output filename for an episode.

    Example: ``Naruto - Ep 01 [1080p].mp4``. The name is derived from an explicit
    ``filename``/``file`` query parameter when present (that is where AnimeUnity puts
    the real name), otherwise from the URL path. A ``[quality]`` tag is only added when
    the token actually looks like a resolution (e.g. ``1080p``).
    """
    parsed = urlparse(download_url)

    # Prefer a real filename carried in the query string; fall back to the path name.
    query = parse_qs(parsed.query)
    candidate = ""
    for key in ("filename", "file", "name"):
        values = query.get(key)
        if values and values[0]:
            candidate = unquote(values[0])
            break
    if not candidate:
        candidate = Path(parsed.path).name  # e.g. "1080p.mp4" or "download"

    ext = Path(candidate).suffix or ".mp4"
    token = Path(candidate).stem
    quality_tag = f" [{token}]" if _QUALITY_PATTERN.match(token or "") else ""

    base = f"{sanitize_name(anime_title)} - Ep {episode_label(episode)}{quality_tag}"
    return sanitize_name(base) + ext


def episode_status(
    existing_names: list[str], anime_title: str, episode: "object",
) -> str | None:
    """Return ``"complete"``, ``"partial"`` or ``None`` for an episode.

    Detection is filename-based (independent of the quality tag): a file is matched when
    it starts with ``"<title> - Ep <label>"`` followed by a space or dot, so ``Ep 10``
    never matches ``Ep 100``.
    """
    prefix = f"{sanitize_name(anime_title)} - Ep {episode_label(episode)}"

    def has(suffix: str) -> bool:
        return any(
            name.startswith(prefix)
            and name.endswith(suffix)
            and len(name) > len(prefix)
            and name[len(prefix)] in (" ", ".")
            for name in existing_names
        )

    if has(".mp4"):
        return "complete"
    if has(".mp4.part"):
        return "partial"
    return None
