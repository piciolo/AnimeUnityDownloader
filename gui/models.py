"""Plain data models used across the GUI.

These are lightweight containers built from the JSON returned by the AnimeUnity
API, decoupled from the network layer so the widgets never touch raw dictionaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Anime:
    """A single anime entry as returned by the archive/search API."""

    id: int
    slug: str
    title: str
    poster: str
    anime_type: str
    dubbed: bool
    episodes_count: int
    status: str
    year: str
    score: str
    plot: str
    genres: list[str] = field(default_factory=list)

    @property
    def path(self) -> str:
        """Return the site-relative anime path, e.g. ``/anime/1469-naruto``."""
        return f"/anime/{self.id}-{self.slug}"

    @property
    def api_id(self) -> str:
        """Return the ``id-slug`` fragment used by the ``info_api`` endpoints."""
        return f"{self.id}-{self.slug}"

    @staticmethod
    def from_record(record: dict) -> "Anime":
        """Build an :class:`Anime` from a raw API record."""
        title = (
            record.get("title")
            or record.get("title_it")
            or record.get("title_eng")
            or record.get("slug")
            or "Sconosciuto"
        )
        return Anime(
            id=int(record.get("id")),
            slug=record.get("slug") or "",
            title=title.strip(),
            poster=record.get("imageurl") or "",
            anime_type=record.get("type") or "",
            dubbed=bool(record.get("dub")),
            episodes_count=int(record.get("episodes_count") or 0),
            status=record.get("status") or "",
            year=str(record.get("date") or ""),
            score=str(record.get("score") or ""),
            plot=record.get("plot") or "",
            genres=[
                genre.get("name", "")
                for genre in (record.get("genres") or [])
                if isinstance(genre, dict)
            ],
        )


@dataclass
class Episode:
    """A single episode belonging to an :class:`Anime`."""

    id: int
    number: str
    file_name: str

    @property
    def number_label(self) -> str:
        """Return a display label like ``Episodio 1``."""
        return f"Episodio {self.number}"

    @property
    def number_value(self) -> float | None:
        """Return the episode number as a float, or ``None`` if not numeric."""
        try:
            return float(self.number)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def from_record(record: dict) -> "Episode":
        """Build an :class:`Episode` from a raw API record."""
        return Episode(
            id=int(record.get("id")),
            number=str(record.get("number") or ""),
            file_name=record.get("file_name") or record.get("link") or "",
        )
