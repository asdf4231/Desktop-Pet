"""Fixed raster artwork and lightweight motion for the desktop companion."""

import math
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)

from mochi_pet.ui.palette import qcolor

ASSET_PATH = Path(__file__).resolve().parents[1] / "assets" / "character.png"
_ASSET_CACHE: QPixmap | None = None


def _asset_pixmap() -> QPixmap:
    """Load the one immutable character image used throughout the app."""
    global _ASSET_CACHE
    if _ASSET_CACHE is None:
        _ASSET_CACHE = QPixmap(str(ASSET_PATH))
    return _ASSET_CACHE


def paint_star(
    painter: QPainter,
    center: QPointF,
    radius: float,
    color: QColor | str,
    *,
    points: int = 5,
    inner_ratio: float = 0.44,
    rotation: float = -90.0,
) -> None:
    path = QPainterPath()
    for index in range(points * 2):
        angle = math.radians(rotation + index * 180.0 / points)
        radius_at = radius if index % 2 == 0 else radius * inner_ratio
        point = QPointF(
            center.x() + math.cos(angle) * radius_at,
            center.y() + math.sin(angle) * radius_at,
        )
        if index == 0:
            path.moveTo(point)
        else:
            path.lineTo(point)
    path.closeSubpath()
    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(color))
    painter.drawPath(path)
    painter.restore()


def paint_sparkle(painter: QPainter, center: QPointF, radius: float, color: QColor | str) -> None:
    """A soft four-point twinkle used by the controls and reaction feedback."""
    path = QPainterPath()
    path.moveTo(center.x(), center.y() - radius)
    path.quadTo(
        center.x() + radius * 0.18, center.y() - radius * 0.18, center.x() + radius, center.y()
    )
    path.quadTo(
        center.x() + radius * 0.18, center.y() + radius * 0.18, center.x(), center.y() + radius
    )
    path.quadTo(
        center.x() - radius * 0.18, center.y() + radius * 0.18, center.x() - radius, center.y()
    )
    path.quadTo(
        center.x() - radius * 0.18, center.y() - radius * 0.18, center.x(), center.y() - radius
    )
    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(color))
    painter.drawPath(path)
    painter.restore()


def bubble_path(rect: QRectF, radius: float, tail: str | None = None, tail_size: float = 9.0):
    """A rounded speech balloon with an optional tail on one edge."""
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    if tail is None:
        return path

    if tail == "bottom":
        tip_x = rect.center().x()
        base_y = rect.bottom() - 1
        triangle = QPainterPath()
        triangle.moveTo(tip_x - tail_size, base_y - 2)
        triangle.lineTo(tip_x + tail_size * 0.2, base_y - 2)
        triangle.lineTo(tip_x - tail_size * 0.35, base_y + tail_size)
    elif tail == "left":
        tip_y = rect.center().y()
        base_x = rect.left() + 1
        triangle = QPainterPath()
        triangle.moveTo(base_x - 2, tip_y - tail_size)
        triangle.lineTo(base_x - 2, tip_y + tail_size * 0.3)
        triangle.lineTo(base_x - tail_size, tip_y + tail_size * 0.1)
    elif tail == "right":
        tip_y = rect.center().y()
        base_x = rect.right() - 1
        triangle = QPainterPath()
        triangle.moveTo(base_x + 2, tip_y - tail_size)
        triangle.lineTo(base_x + 2, tip_y + tail_size * 0.3)
        triangle.lineTo(base_x + tail_size, tip_y + tail_size * 0.1)
    else:
        tip_x = rect.center().x()
        base_y = rect.top() + 1
        triangle = QPainterPath()
        triangle.moveTo(tip_x - tail_size, base_y + 2)
        triangle.lineTo(tip_x + tail_size * 0.2, base_y + 2)
        triangle.lineTo(tip_x - tail_size * 0.35, base_y - tail_size)
    triangle.closeSubpath()
    return path.united(triangle)


def paint_mochi(
    painter: QPainter,
    target: QRectF,
    *,
    mood: str = "idle",
    time: float = 0.0,
    gesture: float = 0.0,
    gaze: float = 0.0,
    blink: bool = False,
    theme: str | None = None,
) -> None:
    """Draw the supplied character with breathing, swaying and reaction motion.

    ``theme`` is accepted only as a compatibility placeholder. Appearance
    colours and the character image itself are intentionally not configurable.
    """
    pixmap = _asset_pixmap()
    if pixmap.isNull() or target.width() <= 0 or target.height() <= 0:
        return

    scale = min(target.width() / pixmap.width(), target.height() / pixmap.height())
    draw_width = pixmap.width() * scale
    draw_height = pixmap.height() * scale
    body = QRectF(
        target.center().x() - draw_width / 2.0,
        target.bottom() - draw_height,
        draw_width,
        draw_height,
    )

    shadow = QRadialGradient(QPointF(body.center().x(), target.bottom() - 2), draw_width * 0.42)
    shadow.setColorAt(0.0, qcolor("#35291F", 72))
    shadow.setColorAt(1.0, qcolor("#35291F", 0))

    breathe = math.sin(time * 2.05)
    sway = math.sin(time * 1.15) * 1.15
    bob = 1.0 + breathe * 0.8
    scale_x = 1.0 + breathe * 0.006
    scale_y = 1.0 - breathe * 0.005

    if mood == "happy":
        bob -= abs(math.sin(gesture * 7.5)) * max(4.0, target.height() * 0.018)
    elif mood == "wave":
        sway = 2.2 + math.sin(gesture * 7.0) * 2.4
    elif mood == "dance":
        sway = math.sin(gesture * 8.5) * 5.5
        bob -= abs(math.sin(gesture * 6.0)) * 5.0
    elif mood == "cheer":
        bob -= abs(math.sin(gesture * 7.0)) * max(5.0, target.height() * 0.022)
        scale_y += abs(math.sin(gesture * 7.0)) * 0.012
    elif mood == "surprise":
        sway = 0.0
        bob -= max(3.0, target.height() * 0.014) * max(0.0, 1.0 - gesture * 2.2)
        scale_x += 0.018 * max(0.0, 1.0 - gesture * 2.8)
        scale_y -= 0.012 * max(0.0, 1.0 - gesture * 2.8)
    elif mood == "sleep":
        sway = -4.0 + math.sin(time * 1.2) * 0.7
        bob = 2.0 + math.sin(time * 1.4)

    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(shadow)
    spread = 1.0 + breathe * 0.018
    painter.drawEllipse(
        QRectF(
            body.center().x() - draw_width * 0.35 * spread,
            target.bottom() - 8.0,
            draw_width * 0.70 * spread,
            max(8.0, draw_height * 0.025),
        )
    )

    pivot = QPointF(body.center().x(), body.bottom())
    painter.translate(0.0, bob)
    painter.translate(pivot)
    painter.rotate(sway)
    painter.scale(scale_x, scale_y)
    painter.translate(-pivot)
    painter.drawPixmap(body, pixmap, QRectF(pixmap.rect()))

    if blink and mood not in ("sleep", "happy", "cheer", "dance"):
        painter.setPen(
            QPen(
                qcolor("#4B2617"),
                max(1.1, draw_width * 0.008),
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
            )
        )
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for x_factor in (0.24, 0.67):
            eye = QRectF(
                body.left() + draw_width * x_factor,
                body.top() + draw_height * 0.226,
                draw_width * 0.13,
                draw_height * 0.046,
            )
            painter.drawArc(eye, 20 * 16, 140 * 16)
    painter.restore()

    if mood in ("happy", "cheer", "dance"):
        colors = ("#F4B943", "#67BFA0")
        for index, (x, y) in enumerate(
            (
                (target.left() + 9, target.top() + target.height() * 0.34),
                (target.right() - 8, target.top() + target.height() * 0.40),
            )
        ):
            pulse = 3.0 + abs(math.sin(gesture * 5.0 + index)) * 2.8
            paint_sparkle(painter, QPointF(x, y), pulse, colors[index])
    elif mood == "sleep":
        painter.save()
        painter.setPen(qcolor("#F4B943", 220))
        font = painter.font()
        font.setPointSizeF(max(8.0, target.height() * 0.045))
        font.setBold(True)
        painter.setFont(font)
        for index, (x, y) in enumerate(((0.78, 0.18), (0.87, 0.12), (0.96, 0.06))):
            painter.drawText(
                QPointF(
                    target.left() + target.width() * x,
                    target.top() + target.height() * y - math.sin(time * 1.5 + index) * 3,
                ),
                "z",
            )
        painter.restore()


def mochi_pixmap(
    size: int,
    mood: str = "idle",
    *,
    gesture: float = 0.4,
    time: float = 0.7,
    theme: str | None = None,
) -> QPixmap:
    """Render the fixed character into a transparent square pixmap."""
    ratio = 2
    pixmap = QPixmap(int(size * ratio), int(size * ratio))
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    margin = pixmap.width() * 0.05
    paint_mochi(
        painter,
        QRectF(
            margin,
            margin,
            pixmap.width() - margin * 2,
            pixmap.height() - margin * 2,
        ),
        mood=mood,
        time=time,
        gesture=gesture,
        theme=theme,
    )
    painter.end()
    pixmap.setDevicePixelRatio(ratio)
    return pixmap


def mochi_icon(size: int = 64, theme: str | None = None) -> QPixmap:
    """A compact badge icon for the tray and application windows."""
    ratio = 2
    pixmap = QPixmap(int(size * ratio), int(size * ratio))
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    badge = QLinearGradient(QPointF(0, 0), QPointF(pixmap.width(), pixmap.height()))
    badge.setColorAt(0.0, qcolor("#EBF8F2"))
    badge.setColorAt(0.55, qcolor("#FFF0D8"))
    badge.setColorAt(1.0, qcolor("#F7D7BE"))
    painter.setPen(QPen(qcolor("#E9CFB5"), max(1.0, pixmap.width() * 0.018)))
    painter.setBrush(badge)
    painter.drawEllipse(QRectF(1, 1, pixmap.width() - 2, pixmap.height() - 2))
    paint_mochi(
        painter,
        QRectF(
            pixmap.width() * 0.12,
            pixmap.height() * 0.08,
            pixmap.width() * 0.76,
            pixmap.height() * 0.84,
        ),
        mood="happy",
        time=0.4,
        gesture=0.55,
        theme=theme,
    )
    painter.end()
    pixmap.setDevicePixelRatio(ratio)
    return pixmap


__all__ = [
    "ASSET_PATH",
    "bubble_path",
    "mochi_icon",
    "mochi_pixmap",
    "paint_mochi",
    "paint_sparkle",
    "paint_star",
]
