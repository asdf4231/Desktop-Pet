"""Shared colour tokens and painting helpers for the Mochi interface.

Every surface (the pet, chat, settings, the training windows) pulls from this module so
the whole app keeps one warm, soft, hand-drawn palette instead of drifting into a
different look per file.
"""

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QFont, QLinearGradient, QRadialGradient

# --- ink -------------------------------------------------------------------
INK = "#4C3B34"
INK_SOFT = "#7B685D"
INK_FAINT = "#A89488"
INK_ON_DARK = "#FFF8EF"

# --- surfaces --------------------------------------------------------------
CREAM = "#FFF9F1"
CREAM_DEEP = "#FCEDDD"
SHELL = "#F7E8D9"
SHELL_DEEP = "#F0DCC8"
CARD = "#FFFFFF"

# --- accents ---------------------------------------------------------------
PEACH = "#FFBB9E"
PEACH_DEEP = "#F4917A"
CORAL = "#EE7C64"
CORAL_DEEP = "#D2604B"
BLUSH = "#F9A9A1"
MINT = "#86CDBA"
MINT_DEEP = "#3E8B79"
TEAL = "#5FA9A0"
GOLD = "#F7C75B"
GOLD_DEEP = "#DBA22F"
LAVENDER = "#BCB1EA"
SKY = "#A6DAEA"
SKY_DEEP = "#6FB6CC"

# --- lines -----------------------------------------------------------------
LINE = "#EADBC9"
LINE_SOFT = "#F4E9DB"

# --- character -------------------------------------------------------------
FUR = "#FFF6E9"
FUR_SHADE = "#FBE3C9"
FUR_MARK = "#FFD9B4"
OUTLINE = "#96705A"
OUTLINE_SOFT = "#B08A72"
EAR_PINK = "#F9B3AC"
NOSE = "#EE8F86"
EYE = "#4A3831"

# --- shared metrics --------------------------------------------------------
RADIUS_CARD = 18
RADIUS_CONTROL = 12
RADIUS_PILL = 999


def qcolor(value: str | QColor, alpha: float | None = None) -> QColor:
    """Return a QColor, optionally with an alpha applied (0.0-1.0 float or 0-255)."""
    color = QColor(value) if isinstance(value, str) else QColor(value)
    if alpha is not None:
        if isinstance(alpha, float) and alpha <= 1.0:
            color.setAlphaF(alpha)
        else:
            color.setAlpha(int(alpha))
    return color


def vertical_gradient(rect: QRectF, top: str, bottom: str) -> QLinearGradient:
    gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    gradient.setColorAt(0.0, QColor(top))
    gradient.setColorAt(1.0, QColor(bottom))
    return gradient


def diagonal_gradient(rect: QRectF, start: str, end: str) -> QLinearGradient:
    gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
    gradient.setColorAt(0.0, QColor(start))
    gradient.setColorAt(1.0, QColor(end))
    return gradient


def radial_glow(center: QPointF, radius: float, inner: str, outer: str) -> QRadialGradient:
    gradient = QRadialGradient(center, radius)
    gradient.setColorAt(0.0, QColor(inner))
    gradient.setColorAt(1.0, QColor(outer))
    return gradient


def ui_font(size: float, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    """A font stack that renders Chinese and Latin consistently on Windows."""
    font = QFont()
    font.setFamilies(["Microsoft YaHei UI", "PingFang SC", "Segoe UI", "Aptos", "sans-serif"])
    font.setPointSizeF(size)
    font.setWeight(weight)
    return font


def with_alpha(value: str, alpha: float) -> QColor:
    return qcolor(value, alpha)
