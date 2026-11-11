"""Articulated animation built from the supplied character artwork."""

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

from shaqiu_pet.ui.palette import qcolor

ASSET_DIR = Path(__file__).resolve().parents[1] / "assets"
ASSET_PATH = ASSET_DIR / "character.png"
_ASSET_CACHE: QPixmap | None = None
_PART_CACHE: dict[str, QPixmap] = {}
ARTICULATED_PARTS = (
    "character_head",
    "character_torso",
    "character_arm_left",
    "character_arm_right",
    "character_leg_left",
    "character_leg_right",
    "character_tail",
)


def _asset_pixmap() -> QPixmap:
    """Load the one immutable character image used throughout the app."""
    global _ASSET_CACHE
    if _ASSET_CACHE is None:
        _ASSET_CACHE = QPixmap(str(ASSET_PATH))
    return _ASSET_CACHE


def _part_pixmap(name: str) -> QPixmap:
    """Load one transparent body-part layer from the fixed source artwork."""
    pixmap = _PART_CACHE.get(name)
    if pixmap is None:
        pixmap = QPixmap(str(ASSET_DIR / f"{name}.png"))
        _PART_CACHE[name] = pixmap
    return pixmap


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


def paint_shaqiu(
    painter: QPainter,
    target: QRectF,
    *,
    mood: str = "idle",
    time: float = 0.0,
    gesture: float = 0.0,
    gaze: float = 0.0,
    blink: bool = False,
    walking: bool = False,
    theme: str | None = None,
) -> None:
    """Draw articulated head, arm, leg and tail motion from the supplied image.

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
    scale_x = body.width() / pixmap.width()
    scale_y = body.height() / pixmap.height()

    shadow = QRadialGradient(QPointF(body.center().x(), target.bottom() - 2), draw_width * 0.42)
    shadow.setColorAt(0.0, qcolor("#35291F", 72))
    shadow.setColorAt(1.0, qcolor("#35291F", 0))

    breathe = math.sin(time * 2.05)
    head_angle = math.sin(time * 0.85) * 0.75
    head_offset_y = breathe * max(0.45, draw_height * 0.0018)
    torso_scale = (1.0 + breathe * 0.006, 1.0 - breathe * 0.004)
    left_arm = 1.7 + math.sin(time * 1.25) * 1.0
    right_arm = -1.7 - math.sin(time * 1.25) * 1.0
    left_leg = math.sin(time * 1.6) * 0.45
    right_leg = -left_leg
    tail_angle = math.sin(time * 2.1) * 3.2
    body_bob = breathe * 0.55

    if walking:
        stride = math.sin(time * 8.5)
        left_leg = stride * 13.0
        right_leg = -stride * 13.0
        left_arm = -stride * 10.0
        right_arm = stride * 10.0
        body_bob -= abs(stride) * max(1.0, draw_height * 0.004)
        head_angle += stride * 0.7
        tail_angle += stride * 3.0
    elif mood == "happy":
        hop = abs(math.sin(gesture * 7.5))
        body_bob -= hop * max(2.0, draw_height * 0.009)
        left_arm += 15.0 + hop * 7.0
        right_arm -= 15.0 + hop * 7.0
        head_angle += math.sin(gesture * 7.5) * 1.1
        torso_scale = (1.0 + hop * 0.008, 1.0 - hop * 0.006)
    elif mood == "wave":
        right_arm = -62.0 + math.sin(gesture * 9.0) * 12.0
        left_arm = 4.0
        head_angle = 3.0 + math.sin(gesture * 4.0) * 0.8
    elif mood == "dance":
        rhythm = math.sin(gesture * 8.5)
        left_arm = 19.0 + rhythm * 24.0
        right_arm = -19.0 - rhythm * 24.0
        left_leg = rhythm * 8.0
        right_leg = -rhythm * 8.0
        head_angle = rhythm * 3.2
        tail_angle += rhythm * 5.0
        body_bob -= abs(rhythm) * max(1.2, draw_height * 0.004)
    elif mood == "cheer":
        lift = abs(math.sin(gesture * 7.0))
        left_arm = 47.0 + lift * 5.0
        right_arm = -47.0 - lift * 5.0
        body_bob -= lift * max(2.5, draw_height * 0.011)
        head_angle = math.sin(gesture * 7.0) * 2.0
        torso_scale = (1.0 - lift * 0.006, 1.0 + lift * 0.010)
    elif mood == "surprise":
        shock = max(0.0, 1.0 - gesture * 2.2)
        left_arm = 26.0 * shock
        right_arm = -26.0 * shock
        head_offset_y -= shock * max(2.0, draw_height * 0.010)
        head_angle = 0.0
        torso_scale = (1.0 + shock * 0.012, 1.0 - shock * 0.008)
    elif mood == "shy":
        left_arm = -9.0
        right_arm = 9.0
        head_angle = -3.2
        head_offset_y += max(0.8, draw_height * 0.003)
    elif mood == "sleep":
        head_angle = -4.2 + math.sin(time * 0.8) * 0.5
        head_offset_y += max(1.0, draw_height * 0.004)
        left_arm = 3.5
        right_arm = -3.5
        torso_scale = (1.0, 0.985)
        tail_angle = math.sin(time * 1.1) * 1.2

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

    def draw_part(
        name: str,
        *,
        angle: float = 0.0,
        pivot: tuple[float, float],
        offset: tuple[float, float] = (0.0, 0.0),
        part_scale: tuple[float, float] = (1.0, 1.0),
    ) -> None:
        part = _part_pixmap(name)
        if part.isNull():
            return
        pivot_point = QPointF(
            body.left() + pivot[0] * scale_x,
            body.top() + pivot[1] * scale_y,
        )
        painter.save()
        painter.translate(offset[0], offset[1])
        painter.translate(pivot_point)
        painter.rotate(angle)
        painter.scale(part_scale[0], part_scale[1])
        painter.translate(-pivot_point)
        painter.drawPixmap(body, part, QRectF(part.rect()))
        painter.restore()

    # Legs and tail sit behind the torso; arms move over the coat.
    draw_part(
        "character_tail",
        angle=tail_angle,
        pivot=(620.0, 1110.0),
        offset=(0.0, body_bob),
    )
    draw_part(
        "character_leg_left",
        angle=left_leg,
        pivot=(285.0, 1135.0),
        offset=(0.0, body_bob),
    )
    draw_part(
        "character_leg_right",
        angle=right_leg,
        pivot=(475.0, 1135.0),
        offset=(0.0, body_bob),
    )
    draw_part(
        "character_torso",
        pivot=(395.0, 1030.0),
        offset=(0.0, body_bob),
        part_scale=torso_scale,
    )
    draw_part(
        "character_arm_left",
        angle=left_arm,
        pivot=(220.0, 710.0),
        offset=(0.0, body_bob),
    )
    draw_part(
        "character_arm_right",
        angle=right_arm,
        pivot=(570.0, 710.0),
        offset=(0.0, body_bob),
    )
    draw_part(
        "character_head",
        angle=head_angle,
        pivot=(395.0, 635.0),
        offset=(0.0, body_bob + head_offset_y),
    )

    if blink and mood not in ("sleep", "happy", "cheer", "dance"):
        head_pivot = QPointF(
            body.left() + 395.0 * scale_x,
            body.top() + 635.0 * scale_y,
        )
        painter.save()
        painter.translate(0.0, body_bob + head_offset_y)
        painter.translate(head_pivot)
        painter.rotate(head_angle)
        painter.translate(-head_pivot)
        painter.translate(body.topLeft())
        painter.scale(scale_x, scale_y)
        painter.setPen(
            QPen(
                qcolor("#4B2617"),
                8.0,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
            )
        )
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for eye in (QRectF(150, 320, 105, 62), QRectF(535, 320, 105, 62)):
            painter.drawArc(eye, 20 * 16, 140 * 16)
        painter.restore()
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


def shaqiu_pixmap(
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
    paint_shaqiu(
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


def shaqiu_icon(size: int = 64, theme: str | None = None) -> QPixmap:
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
    paint_shaqiu(
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
    "ARTICULATED_PARTS",
    "bubble_path",
    "shaqiu_icon",
    "shaqiu_pixmap",
    "paint_shaqiu",
    "paint_sparkle",
    "paint_star",
]
