"""Custom-painted controls, so buttons match the hand-drawn pet artwork."""

import math

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton, QSizePolicy, QWidget

from shaqiu_pet.ui.art import paint_sparkle
from shaqiu_pet.ui.palette import (
    CORAL,
    CORAL_DEEP,
    CREAM_DEEP,
    GOLD,
    GOLD_DEEP,
    INK,
    INK_FAINT,
    LINE,
    MINT,
    MINT_DEEP,
    OUTLINE,
    PEACH_DEEP,
    SHELL,
    SHELL_DEEP,
    qcolor,
    ui_font,
)

# tone -> (top, bottom, hover top, hover bottom, pressed, ink, shadow)
TONES: dict[str, tuple[str, str, str, str, str, str, str]] = {
    "coral": ("#FAA48B", CORAL, "#FFB79F", PEACH_DEEP, CORAL_DEEP, "#FFFFFF", CORAL_DEEP),
    "cream": ("#FFFFFF", CREAM_DEEP, "#FFFFFF", "#F8E6D3", SHELL_DEEP, INK, OUTLINE),
    "mint": ("#A5E2CF", MINT, "#B7EAD9", "#74C6AF", MINT_DEEP, "#FFFFFF", MINT_DEEP),
    "gold": ("#FFDC84", GOLD, "#FFE59C", "#EFB944", GOLD_DEEP, "#5A3F12", GOLD_DEEP),
    "ghost": ("#00000000", "#00000000", "#FFF3E6", "#FBE7D3", SHELL_DEEP, INK_FAINT, OUTLINE),
}
DISABLED_TONE = (SHELL, SHELL_DEEP, SHELL, SHELL_DEEP, SHELL_DEEP, "#FFFFFF", OUTLINE)


def _lerp(start: str | QColor, end: str | QColor, amount: float) -> QColor:
    """Blend two colours; PySide6 does not expose QColor.interpolate()."""
    source = qcolor(start)
    target = qcolor(end)
    ratio = max(0.0, min(1.0, amount))
    return QColor(
        int(source.red() + (target.red() - source.red()) * ratio),
        int(source.green() + (target.green() - source.green()) * ratio),
        int(source.blue() + (target.blue() - source.blue()) * ratio),
        int(source.alpha() + (target.alpha() - source.alpha()) * ratio),
    )


class PaintedButton(QAbstractButton):
    """A soft, rounded, gently animated button."""

    def __init__(
        self,
        text: str,
        accent: bool = True,
        parent: QWidget | None = None,
        *,
        tone: str | None = None,
        icon: str | None = None,
        compact: bool = False,
    ):
        super().__init__(parent)
        self.setText(text)
        self.accent = accent
        self.tone = tone or ("coral" if accent else "cream")
        self.icon = icon
        self.compact = compact
        self._hover = 0.0
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(30 if compact else 38)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(150)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.valueChanged.connect(self._on_animation)

    def _on_animation(self, value) -> None:
        self._hover = float(value)
        self.update()

    def _animate_to(self, target: float) -> None:
        self._animation.stop()
        self._animation.setStartValue(self._hover)
        self._animation.setEndValue(target)
        self._animation.start()

    def enterEvent(self, event):
        self._animate_to(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animate_to(0.0)
        super().leaveEvent(event)

    def sizeHint(self) -> QSize:
        metrics = QFontMetrics(self.font())
        icon_room = 22 if self.icon else 0
        vertical = 30 if self.compact else 40
        return QSize(metrics.horizontalAdvance(self.text()) + 34 + icon_room, vertical)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        radius = 11.0 if self.compact else 13.0
        rect = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)
        if self.isDown():
            rect = rect.translated(0.0, 1.5)

        enabled = self.isEnabled()
        if not enabled:
            top, bottom, hover_top, hover_bottom, pressed, ink, shadow = DISABLED_TONE
        else:
            top, bottom, hover_top, hover_bottom, pressed, ink, shadow = TONES.get(
                self.tone, TONES["coral"]
            )
        amount = self._hover if enabled else 0.0

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(qcolor(shadow, 46 if enabled else 20))
        painter.drawRoundedRect(rect.translated(0.0, 2.6), radius, radius)

        if self.isDown():
            fill_top, fill_bottom = _lerp(top, pressed, 0.7), qcolor(pressed)
        else:
            fill_top = _lerp(top, hover_top, amount)
            fill_bottom = _lerp(bottom, hover_bottom, amount)
        if self.tone == "ghost" and amount < 0.02:
            painter.setBrush(Qt.BrushStyle.NoBrush)
        else:
            gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
            gradient.setColorAt(0.0, fill_top)
            gradient.setColorAt(1.0, fill_bottom)
            painter.setBrush(gradient)
        painter.setPen(
            QPen(qcolor(LINE, 150), 1.0) if self.tone in ("cream", "ghost") else Qt.PenStyle.NoPen
        )
        painter.drawRoundedRect(rect, radius, radius)

        # glossy top edge
        if self.tone != "ghost" or amount > 0.02:
            painter.setPen(QPen(qcolor("#FFFFFF", 90), 1.2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(1.6, 1.4, -1.6, -1.6), radius - 1, radius - 1)

        text_left = rect.left()
        if self.icon:
            self._paint_icon(painter, QPointF(rect.left() + 17, rect.center().y()), qcolor(ink))
            text_left += 22
        painter.setPen(qcolor(ink))
        painter.setFont(ui_font(9 if self.compact else 9.5, QFont.Weight.DemiBold))
        painter.drawText(
            QRectF(text_left, rect.top(), rect.right() - text_left, rect.height()),
            Qt.AlignmentFlag.AlignCenter,
            self.text(),
        )

    def _paint_icon(self, painter: QPainter, center: QPointF, ink: QColor) -> None:
        painter.save()
        painter.translate(center)
        if self.icon == "chat":
            painter.setPen(QPen(ink, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(-7, -6, 14, 10.5), 3.6, 3.6)
            painter.drawLine(QPointF(-1.6, 4.6), QPointF(-4.0, 7.6))
        elif self.icon == "send":
            painter.setPen(QPen(ink, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(QPointF(-6, 0), QPointF(6, 0))
            painter.drawLine(QPointF(1.6, -4.4), QPointF(6.2, 0))
            painter.drawLine(QPointF(1.6, 4.4), QPointF(6.2, 0))
        elif self.icon == "gear":
            painter.setPen(QPen(ink, 1.7))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(0, 0), 3.4, 3.4)
            for index in range(6):
                angle = math.tau * index / 6
                painter.drawLine(
                    QPointF(math.cos(angle) * 5.2, math.sin(angle) * 5.2),
                    QPointF(math.cos(angle) * 7.4, math.sin(angle) * 7.4),
                )
        else:
            paint_sparkle(painter, QPointF(0, 0), 6.4, ink)
        painter.restore()


class PaintedPill(QWidget):
    """A small rounded status pill used for the scoreboards."""

    def __init__(self, text: str, tone: str = "gold", parent: QWidget | None = None):
        super().__init__(parent)
        self.text = text
        self.tone = tone
        self.setMinimumHeight(34)
        self.setMinimumWidth(96)

    def setText(self, text: str):
        self.text = text
        self.updateGeometry()
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(max(96, QFontMetrics(self.font()).horizontalAdvance(self.text) + 34), 34)

    def paintEvent(self, _event):
        colors = {
            "gold": ("#FFE7A8", GOLD, "#6B4A12"),
            "mint": ("#D8F2E7", "#A9DECB", MINT_DEEP),
            "coral": ("#FFE1D6", "#FBC0AE", "#8B4E43"),
            "dark": ("#4A3B34", "#332823", "#FFF6EA"),
            "plain": ("#FFFFFF", CREAM_DEEP, INK),
        }
        top, bottom, ink = colors.get(self.tone, colors["gold"])
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(qcolor(OUTLINE, 30))
        painter.drawRoundedRect(rect.translated(0, 2.2), 14, 14)
        gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        gradient.setColorAt(0.0, qcolor(top))
        gradient.setColorAt(1.0, qcolor(bottom))
        painter.setBrush(gradient)
        painter.drawRoundedRect(rect, 14, 14)
        painter.setPen(QPen(qcolor("#FFFFFF", 80), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(1.4, 1.2, -1.4, -1.4), 12.5, 12.5)
        painter.setPen(qcolor(ink))
        painter.setFont(ui_font(9, QFont.Weight.Bold))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text)


__all__ = ["PaintedButton", "PaintedPill"]
