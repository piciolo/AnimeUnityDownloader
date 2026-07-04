"""Graphical interface package for the AnimeUnity Downloader.

This package adds a desktop GUI (PySide6) on top of the same download flow used by
the original command-line tool: it searches/browses AnimeUnity directly, lists
episodes and downloads the direct ``.mp4`` files with progress tracking.

The command-line tool in the project root keeps working unchanged; this package is
self-contained so it can be packaged into a standalone Windows executable.
"""

__all__ = ["__version__"]

__version__ = "1.1.0"
