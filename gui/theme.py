"""Dark theme (Qt style sheet + palette) for the application."""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette

# Palette
BG = "#12131a"
BG_ALT = "#1a1c26"
CARD = "#20222e"
CARD_HOVER = "#2a2d3d"
BORDER = "#2e3140"
TEXT = "#e8e9f0"
TEXT_DIM = "#9aa0b4"
ACCENT = "#7c5cff"
ACCENT_HOVER = "#9179ff"
ACCENT_PRESSED = "#6a4de0"
GOOD = "#3ecf8e"
BAD = "#ff5c72"

APP_QSS = f"""
* {{
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
    color: {TEXT};
    outline: none;
}}

QMainWindow, QWidget#Root {{
    background: {BG};
}}

QLabel {{ background: transparent; }}
QLabel#Title {{ font-size: 22px; font-weight: 700; }}
QLabel#Subtitle {{ color: {TEXT_DIM}; }}
QLabel#SectionTitle {{ font-size: 16px; font-weight: 600; }}
QLabel#Muted {{ color: {TEXT_DIM}; }}

/* Search bar */
QLineEdit {{
    background: {BG_ALT};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 9px 12px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus {{ border: 1px solid {ACCENT}; }}

QComboBox {{
    background: {BG_ALT};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 8px 12px;
    min-width: 120px;
}}
QComboBox:focus, QComboBox:hover {{ border: 1px solid {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {CARD};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT};
    padding: 4px;
}}

/* Buttons */
QPushButton {{
    background: {BG_ALT};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 8px 16px;
    font-weight: 600;
}}
QPushButton:hover {{ background: {CARD_HOVER}; border-color: {ACCENT}; }}
QPushButton:pressed {{ background: {CARD}; }}
QPushButton:disabled {{ color: {TEXT_DIM}; border-color: {BORDER}; }}

QPushButton#Primary {{
    background: {ACCENT};
    border: none;
    color: white;
}}
QPushButton#Primary:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#Primary:pressed {{ background: {ACCENT_PRESSED}; }}
QPushButton#Primary:disabled {{ background: {BORDER}; color: {TEXT_DIM}; }}

QPushButton#Ghost {{ background: transparent; border: 1px solid {BORDER}; }}
QPushButton#Ghost:hover {{ border-color: {ACCENT}; }}

QPushButton#BackButton {{
    background: {CARD};
    border: 1px solid {ACCENT};
    color: {ACCENT_HOVER};
    padding: 8px 18px;
    font-weight: 700;
}}
QPushButton#BackButton:hover {{ background: {ACCENT}; color: white; border-color: {ACCENT}; }}
QPushButton#BackButton:pressed {{ background: {ACCENT_PRESSED}; }}

QPushButton#Danger:hover {{ border-color: {BAD}; color: {BAD}; }}

/* Cards */
QFrame#Card {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 14px;
}}
QFrame#Card:hover {{ border: 1px solid {ACCENT}; background: {CARD_HOVER}; }}
QLabel#CardTitle {{ font-weight: 600; }}
QLabel#Badge {{
    background: {BG};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 2px 6px;
    color: {TEXT_DIM};
    font-size: 11px;
}}
QLabel#BadgeDub {{
    background: rgba(124, 92, 255, 0.18);
    border: 1px solid {ACCENT};
    color: {ACCENT_HOVER};
    border-radius: 8px;
    padding: 2px 6px;
    font-size: 11px;
}}

/* Tabs */
QTabWidget::pane {{ border: none; background: {BG}; }}
QStackedWidget, QScrollArea > QWidget > QWidget {{ background: {BG}; }}
QTabBar::tab {{
    background: transparent;
    color: {TEXT_DIM};
    padding: 8px 18px;
    border: none;
    border-bottom: 2px solid transparent;
    font-weight: 600;
}}
QTabBar::tab:selected {{ color: {TEXT}; border-bottom: 2px solid {ACCENT}; }}
QTabBar::tab:hover {{ color: {TEXT}; }}

/* Scroll areas */
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{
    background: transparent; width: 10px; margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER}; border-radius: 5px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {ACCENT}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar:horizontal {{ height: 10px; background: transparent; }}
QScrollBar::handle:horizontal {{ background: {BORDER}; border-radius: 5px; }}

/* Progress bars */
QProgressBar {{
    background: {BG};
    border: 1px solid {BORDER};
    border-radius: 7px;
    height: 14px;
    text-align: center;
    font-size: 10px;
    color: {TEXT_DIM};
}}
QProgressBar::chunk {{
    background: {ACCENT};
    border-radius: 6px;
}}

/* Checkboxes */
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 18px; height: 18px;
    border: 1px solid {BORDER};
    border-radius: 5px;
    background: {BG_ALT};
}}
QCheckBox::indicator:hover {{ border-color: {ACCENT}; }}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
    image: url(none);
}}

/* Episode list */
QListWidget {{
    background: {BG_ALT};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 6px;
    color: {TEXT};
}}
QListWidget::item {{
    background: transparent;
    color: {TEXT};
    padding: 9px 10px;
    margin: 2px 2px;
    border-radius: 8px;
}}
QListWidget::item:hover {{ background: {CARD_HOVER}; }}
QListWidget::item:selected {{
    background: rgba(124, 92, 255, 0.20);
    color: {TEXT};
}}
QListWidget::indicator {{
    width: 18px; height: 18px;
    border: 1px solid {BORDER};
    border-radius: 5px;
    background: {CARD};
    margin-right: 4px;
}}
QListWidget::indicator:hover {{ border-color: {ACCENT}; }}
QListWidget::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}

/* Spin boxes */
QSpinBox {{
    background: {BG_ALT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px 8px;
    min-width: 54px;
}}
QSpinBox:focus {{ border: 1px solid {ACCENT}; }}
QSpinBox::up-button, QSpinBox::down-button {{
    width: 16px;
    background: {CARD};
    border: none;
}}
QSpinBox::up-button {{ border-top-right-radius: 8px; }}
QSpinBox::down-button {{ border-bottom-right-radius: 8px; }}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background: {CARD_HOVER}; }}
QSpinBox::up-arrow {{
    image: none; width: 0; height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid {TEXT_DIM};
}}
QSpinBox::down-arrow {{
    image: none; width: 0; height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {TEXT_DIM};
}}

/* Rows */
QFrame#Row {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
QFrame#Divider {{ background: {BORDER}; max-height: 1px; }}

QToolTip {{
    background: {CARD};
    color: {TEXT};
    border: 1px solid {ACCENT};
    padding: 6px;
    border-radius: 6px;
}}
"""


def build_palette() -> QPalette:
    """Return a dark palette so every widget (even unstyled containers, tab pages and
    scroll viewports) renders on the dark background instead of the light default."""
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(BG))
    palette.setColor(QPalette.WindowText, QColor(TEXT))
    palette.setColor(QPalette.Base, QColor(BG_ALT))
    palette.setColor(QPalette.AlternateBase, QColor(CARD))
    palette.setColor(QPalette.Text, QColor(TEXT))
    palette.setColor(QPalette.Button, QColor(BG_ALT))
    palette.setColor(QPalette.ButtonText, QColor(TEXT))
    palette.setColor(QPalette.BrightText, QColor("#ffffff"))
    palette.setColor(QPalette.Highlight, QColor(ACCENT))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ToolTipBase, QColor(CARD))
    palette.setColor(QPalette.ToolTipText, QColor(TEXT))
    palette.setColor(QPalette.PlaceholderText, QColor(TEXT_DIM))
    palette.setColor(QPalette.Link, QColor(ACCENT))

    disabled = QPalette.Disabled
    palette.setColor(disabled, QPalette.WindowText, QColor(TEXT_DIM))
    palette.setColor(disabled, QPalette.Text, QColor(TEXT_DIM))
    palette.setColor(disabled, QPalette.ButtonText, QColor(TEXT_DIM))
    return palette
