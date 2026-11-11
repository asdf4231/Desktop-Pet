"""Three focused attention-training activities with persistent best times."""

import random
import time

from PySide6.QtCore import QPointF, QRectF, QRegularExpression, Qt, QTimer, Signal
from PySide6.QtGui import (
    QFont,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPen,
    QRegularExpressionValidator,
    QShortcut,
)
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from shaqiu_pet.settings import TrainingHistoryStore, TrainingRecord
from shaqiu_pet.training import SchulteSession, format_duration
from shaqiu_pet.ui.controls import PaintedButton, PaintedPill
from shaqiu_pet.ui.palette import INK, MINT_DEEP, qcolor, ui_font

VISION_PREFLASH_MS = 80
VISION_NUMBER_MS = 340


def _repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def _history_text(store: TrainingHistoryStore, kind: str, limit: int = 6) -> str:
    records = store.records(kind, limit=limit)
    if not records:
        return "还没有记录。完成一局后，这里会保存每次用时。"
    lines = []
    for record in records:
        stamp = record.played_at[5:16].replace("T", " ")
        extra = " · 正确" if kind == "vision" and record.success else ""
        lines.append(f"{stamp}    {format_duration(record.duration_ms)}{extra}")
    return "\n".join(lines)


class SchulteWindow(QWidget):
    """Continuous 1-50 training on a fixed 5x5 board."""

    def __init__(self, history_store: TrainingHistoryStore):
        super().__init__()
        self.history_store = history_store
        self.session: SchulteSession | None = None
        self._started_at = 0.0
        self.elapsed_ms = 0
        self.setObjectName("trainingWindow")
        self.setWindowTitle("shaqiu | 舒尔特方格")
        self.resize(900, 700)
        self.setMinimumSize(760, 620)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 24)
        root.setSpacing(12)
        eyebrow = QLabel("ATTENTION TRAINING  /  01")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("舒尔特方格")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "从 1 点 2，依次到 50。每完成一个 1–25 数字，它会在原位置变成对应的 26–50。"
        )
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        root.addWidget(eyebrow)
        root.addWidget(title)
        root.addWidget(subtitle)

        content = QHBoxLayout()
        content.setSpacing(18)

        board_card = QFrame()
        board_card.setObjectName("card")
        board_layout = QVBoxLayout(board_card)
        board_layout.setContentsMargins(16, 16, 16, 16)
        board_layout.setSpacing(10)
        self.progress_label = QLabel("准备好后点击开始")
        self.progress_label.setObjectName("sectionTitle")
        board_layout.addWidget(self.progress_label)
        self.grid = QGridLayout()
        self.grid.setSpacing(7)
        self.cells: list[QPushButton] = []
        for index in range(25):
            button = QPushButton("·")
            button.setObjectName("schulteCell")
            button.setMinimumSize(72, 72)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setEnabled(False)
            button.clicked.connect(lambda _checked=False, cell=index: self._click_cell(cell))
            self.cells.append(button)
            self.grid.addWidget(button, index // 5, index % 5)
        board_layout.addLayout(self.grid, 1)
        self.status = QLabel("点击开始计时")
        self.status.setObjectName("muted")
        board_layout.addWidget(self.status)
        content.addWidget(board_card, 3)

        side = QVBoxLayout()
        side.setSpacing(12)
        stat_card = QFrame()
        stat_card.setObjectName("card")
        stat_layout = QVBoxLayout(stat_card)
        stat_layout.setContentsMargins(16, 16, 16, 16)
        stat_layout.setSpacing(10)
        stat_title = QLabel("计时")
        stat_title.setObjectName("sectionTitle")
        self.timer_label = QLabel("00.00 秒")
        self.timer_label.setObjectName("trainingMetric")
        self.best_pill = PaintedPill("最快  --", "gold")
        self.last_label = QLabel("最近一次：--")
        self.last_label.setObjectName("muted")
        self.start_button = PaintedButton("开始训练")
        self.start_button.clicked.connect(self.start)
        stat_layout.addWidget(stat_title)
        stat_layout.addWidget(self.timer_label)
        stat_layout.addWidget(self.best_pill)
        stat_layout.addWidget(self.last_label)
        stat_layout.addWidget(self.start_button)
        side.addWidget(stat_card)

        history_card = QFrame()
        history_card.setObjectName("card")
        history_layout = QVBoxLayout(history_card)
        history_layout.setContentsMargins(16, 16, 16, 16)
        history_title = QLabel("每次用时")
        history_title.setObjectName("sectionTitle")
        self.history = QPlainTextEdit()
        self.history.setReadOnly(True)
        self.history.setMinimumHeight(190)
        history_layout.addWidget(history_title)
        history_layout.addWidget(self.history, 1)
        side.addWidget(history_card, 1)
        content.addLayout(side, 2)
        root.addLayout(content, 1)

        self.tick_timer = QTimer(self)
        self.tick_timer.setInterval(50)
        self.tick_timer.timeout.connect(self._update_timer)
        self._refresh_stats()

    def start(self) -> None:
        self.session = SchulteSession()
        self._started_at = time.monotonic()
        self.elapsed_ms = 0
        self.timer_label.setText("00.00 秒")
        self.status.setText("从 1 开始，点击顺序不能跳过。")
        for button, value in zip(self.cells, self.session.cells, strict=True):
            button.setText(str(value))
            button.setEnabled(True)
            button.setProperty("state", "normal")
            _repolish(button)
        self._update_progress()
        self.tick_timer.start()

    def _click_cell(self, index: int) -> None:
        if self.session is None:
            return
        result = self.session.click(index)
        button = self.cells[index]
        if result == "wrong":
            button.setProperty("state", "wrong")
            _repolish(button)
            self.status.setText(f"当前应该点击 {self.session.next_number}")
            QTimer.singleShot(
                220,
                self,
                lambda: self._clear_cell_state(button),
            )
            return

        value = self.session.cells[index]
        button.setText("" if value is None else str(value))
        button.setProperty("state", "correct")
        _repolish(button)
        QTimer.singleShot(170, self, lambda: self._clear_cell_state(button))

        if result == "complete":
            self._finish()
            return
        if self.session.next_number == 26:
            self.status.setText("第一阶段完成，继续从 26 点到 50。")
        else:
            self.status.setText(f"很好，下一个是 {self.session.next_number}")
        self._update_progress()

    @staticmethod
    def _clear_cell_state(button: QPushButton) -> None:
        button.setProperty("state", "normal")
        _repolish(button)

    def _update_progress(self) -> None:
        if self.session is None:
            return
        self.progress_label.setText(
            f"第 {self.session.phase} 阶段 · 已点击 {self.session.progress}/50 · "
            f"下一个 {self.session.next_number if not self.session.finished else '完成'}"
        )

    def _update_timer(self) -> None:
        self.elapsed_ms = round((time.monotonic() - self._started_at) * 1000)
        self.timer_label.setText(f"{self.elapsed_ms / 1000:.2f} 秒")

    def _finish(self) -> None:
        self.tick_timer.stop()
        self.elapsed_ms = round((time.monotonic() - self._started_at) * 1000)
        self.timer_label.setText(f"{self.elapsed_ms / 1000:.2f} 秒")
        self.progress_label.setText("50 / 50 · 训练完成")
        self.status.setText("完成！这一局已经记录。")
        for button in self.cells:
            button.setEnabled(False)
        self.history_store.add(
            TrainingRecord(kind="schulte", duration_ms=self.elapsed_ms, success=True)
        )
        self._refresh_stats()

    def _refresh_stats(self) -> None:
        best = self.history_store.fastest_ms("schulte")
        records = self.history_store.records("schulte")
        self.best_pill.setText(f"最快  {format_duration(best)}")
        self.last_label.setText(
            f"最近一次：{format_duration(records[0].duration_ms)}" if records else "最近一次：--"
        )
        self.history.setPlainText(_history_text(self.history_store, "schulte"))


class ReactionArena(QWidget):
    """A red waiting surface that turns green when the player may click."""

    became_green = Signal()
    valid_click = Signal(int)
    early_click = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("reactionArena")
        self.setMinimumHeight(310)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.state = "idle"
        self._green_at = 0.0
        self.delay_ms = 0
        self._delay_timer = QTimer(self)
        self._delay_timer.setSingleShot(True)
        self._delay_timer.timeout.connect(self._turn_green)

    def start(self) -> None:
        self._delay_timer.stop()
        self.state = "waiting"
        self.delay_ms = random.randint(1500, 4200)
        self._delay_timer.start(self.delay_ms)
        self.update()

    def _turn_green(self, *, now: float | None = None) -> None:
        if self.state != "waiting":
            return
        self.state = "green"
        self._green_at = time.monotonic() if now is None else now
        self.became_green.emit()
        self.update()

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self.state == "waiting":
            self._delay_timer.stop()
            self.state = "early"
            self.early_click.emit()
            self.update()
            return
        if self.state == "green":
            duration = max(1, round((time.monotonic() - self._green_at) * 1000))
            self.state = "result"
            self.valid_click.emit(duration)
            self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bounds = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        if self.state == "green":
            top, bottom = "#55D79C", "#2FA774"
            heading = "现在点击！"
            hint = "越快越好"
        elif self.state == "waiting":
            top, bottom = "#F07A6D", "#C94B46"
            heading = "等待绿色"
            hint = "看到背景变绿后，立刻点击窗口"
        elif self.state == "early":
            top, bottom = "#E7B85D", "#C98E31"
            heading = "抢跑了"
            hint = "重新开始，等屏幕变绿再点击"
        elif self.state == "result":
            top, bottom = "#6FCFB0", "#3E9D82"
            heading = "已记录"
            hint = "点击“再测一次”继续"
        else:
            top, bottom = "#F4E7D9", "#E8D8C6"
            heading = "准备好"
            hint = "红色时不要点"

        gradient = QLinearGradient(bounds.topLeft(), bounds.bottomRight())
        gradient.setColorAt(0.0, qcolor(top))
        gradient.setColorAt(1.0, qcolor(bottom))
        painter.setPen(QPen(qcolor("#FFFFFF", 105), 2.0))
        painter.setBrush(gradient)
        painter.drawRoundedRect(bounds, 25, 25)

        ink = qcolor("#FFFFFF" if self.state in ("green", "waiting") else INK)
        painter.setPen(ink)
        painter.setFont(ui_font(27, QFont.Weight.Bold))
        painter.drawText(bounds.adjusted(20, 24, -20, -54), Qt.AlignmentFlag.AlignCenter, heading)
        painter.setFont(ui_font(11))
        painter.drawText(bounds.adjusted(20, 104, -20, -24), Qt.AlignmentFlag.AlignCenter, hint)
        if self.state == "green":
            painter.setPen(QPen(qcolor("#FFFFFF", 78), 2.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(bounds.center().x(), bounds.center().y()), 76, 76)


class ReactionWindow(QWidget):
    def __init__(self, history_store: TrainingHistoryStore):
        super().__init__()
        self.history_store = history_store
        self.setObjectName("trainingWindow")
        self.setWindowTitle("shaqiu | 反应训练")
        self.resize(760, 640)
        self.setMinimumSize(660, 570)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 24)
        root.setSpacing(12)
        eyebrow = QLabel("ATTENTION TRAINING  /  02")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("反应训练")
        title.setObjectName("pageTitle")
        subtitle = QLabel("窗口是红色时保持等待；变成绿色后，立即点击窗口任意位置。")
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        root.addWidget(eyebrow)
        root.addWidget(title)
        root.addWidget(subtitle)

        self.arena = ReactionArena()
        self.arena.became_green.connect(self._on_green)
        self.arena.valid_click.connect(self._on_valid_click)
        self.arena.early_click.connect(self._on_early_click)
        root.addWidget(self.arena, 1)

        bottom = QHBoxLayout()
        bottom.setSpacing(10)
        self.result_label = QLabel("点击开始准备")
        self.result_label.setObjectName("sectionTitle")
        self.best_pill = PaintedPill("最快  --", "mint")
        self.start_button = PaintedButton("开始准备")
        self.start_button.clicked.connect(self.start)
        bottom.addWidget(self.result_label, 1)
        bottom.addWidget(self.best_pill)
        bottom.addWidget(self.start_button)
        root.addLayout(bottom)

        self.history_card = QFrame()
        self.history_card.setObjectName("card")
        history_layout = QHBoxLayout(self.history_card)
        history_layout.setContentsMargins(14, 10, 14, 10)
        history_title = QLabel("最近记录")
        history_title.setObjectName("fieldLabel")
        self.history_label = QLabel()
        self.history_label.setObjectName("muted")
        self.history_label.setWordWrap(True)
        history_layout.addWidget(history_title)
        history_layout.addWidget(self.history_label, 1)
        root.addWidget(self.history_card)
        self._refresh_stats()

    def start(self) -> None:
        self.result_label.setText("红色阶段：不要点击")
        self.arena.start()

    def _on_green(self) -> None:
        self.result_label.setText("绿色！立即点击")

    def _on_early_click(self) -> None:
        self.result_label.setText("抢跑了，等绿色再点击")

    def _on_valid_click(self, duration_ms: int) -> None:
        self.result_label.setText(f"本次反应：{format_duration(duration_ms)}")
        self.history_store.add(
            TrainingRecord(kind="reaction", duration_ms=duration_ms, success=True)
        )
        self._refresh_stats()

    def _refresh_stats(self) -> None:
        best = self.history_store.fastest_ms("reaction")
        records = self.history_store.records("reaction", limit=5)
        self.best_pill.setText(f"最快  {format_duration(best)}")
        self.history_label.setText(
            "   ·   ".join(format_duration(record.duration_ms) for record in records)
            or "还没有有效记录"
        )


class VisionDisplay(QWidget):
    """A large high-contrast surface used for the number flash."""

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(250)
        self.state = "idle"
        self.number = ""

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        if self.state == "flash":
            top, bottom = "#FFFDF4", "#FFF1C8"
            ink = "#7C5012"
        elif self.state == "showing":
            top, bottom = "#D9F4EA", "#AFE3D2"
            ink = "#164C43"
        elif self.state == "correct":
            top, bottom = "#D8F2E7", "#A9DECB"
            ink = MINT_DEEP
        elif self.state == "wrong":
            top, bottom = "#FFE1D6", "#F9B6A5"
            ink = "#8B4E43"
        else:
            top, bottom = "#3D3348", "#292431"
            ink = "#FFF5E7"
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0.0, qcolor(top))
        gradient.setColorAt(1.0, qcolor(bottom))
        painter.setPen(QPen(qcolor("#FFFFFF", 90), 2.0))
        painter.setBrush(gradient)
        painter.drawRoundedRect(rect, 25, 25)

        painter.setPen(qcolor(ink))
        if self.state in ("countdown", "showing"):
            text = str(self.number)
            painter.setFont(ui_font(48, QFont.Weight.Bold))
        elif self.state == "flash":
            text = "准备看清"
            painter.setFont(ui_font(18, QFont.Weight.Bold))
        elif self.state == "hidden":
            text = "请输入刚才的数字"
            painter.setFont(ui_font(17, QFont.Weight.Bold))
        elif self.state == "correct":
            text = "正确"
            painter.setFont(ui_font(28, QFont.Weight.Bold))
        elif self.state == "wrong":
            text = "再试一次"
            painter.setFont(ui_font(28, QFont.Weight.Bold))
        else:
            text = "点击开始后，专注屏幕"
            painter.setFont(ui_font(18, QFont.Weight.Bold))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)


class VisionWindow(QWidget):
    def __init__(self, history_store: TrainingHistoryStore):
        super().__init__()
        self.history_store = history_store
        self.target = ""
        self.response_started = 0.0
        self.setObjectName("trainingWindow")
        self.setWindowTitle("shaqiu | 动态视力")
        self.resize(720, 610)
        self.setMinimumSize(620, 540)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 24)
        root.setSpacing(12)
        eyebrow = QLabel("ATTENTION TRAINING  /  03")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("动态视力")
        title.setObjectName("pageTitle")
        subtitle = QLabel("开始后屏幕会短暂闪烁 6 位数字；数字消失后，把它输入到下方。")
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        root.addWidget(eyebrow)
        root.addWidget(title)
        root.addWidget(subtitle)

        self.display = VisionDisplay()
        root.addWidget(self.display, 1)

        answer_row = QHBoxLayout()
        answer_row.setSpacing(10)
        self.answer = QLineEdit()
        self.answer.setPlaceholderText("输入刚才的 6 位数字")
        self.answer.setMaxLength(6)
        self.answer.setValidator(QRegularExpressionValidator(QRegularExpression(r"\d{0,6}"), self))
        self.answer.setEnabled(False)
        self.answer.returnPressed.connect(self.submit)
        self.submit_button = PaintedButton("确认答案")
        self.submit_button.clicked.connect(self.submit)
        self.submit_button.setEnabled(False)
        self.start_button = PaintedButton("开始闪示", tone="mint")
        self.start_button.clicked.connect(self.start)
        answer_row.addWidget(self.answer, 1)
        answer_row.addWidget(self.submit_button)
        answer_row.addWidget(self.start_button)
        root.addLayout(answer_row)

        lower = QHBoxLayout()
        self.status = QLabel("准备好后点击开始")
        self.status.setObjectName("muted")
        self.recent_label = QLabel("最近：--")
        self.recent_label.setObjectName("muted")
        self.recent_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        lower.addWidget(self.status, 1)
        lower.addWidget(self.recent_label)
        root.addLayout(lower)

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._next_step)
        self._countdown = 3
        self._answer_state = False
        self.shortcut = QShortcut(QKeySequence("Space"), self)
        self.shortcut.activated.connect(self.start)
        self._refresh_recent()

    def start(self) -> None:
        if self._answer_state or self.display.state in ("countdown", "flash", "showing"):
            return
        self.timer.stop()
        self.target = f"{random.randint(0, 999999):06d}"
        self._countdown = 3
        self.display.state = "countdown"
        self.display.number = self._countdown
        self.display.update()
        self.status.setText("准备，不要移开视线")
        self.answer.clear()
        self.answer.setEnabled(False)
        self.submit_button.setEnabled(False)
        self.timer.start(650)

    def _next_step(self) -> None:
        if self.display.state == "countdown" and self._countdown > 1:
            self._countdown -= 1
            self.display.number = self._countdown
            self.display.update()
            self.timer.start(650)
            return
        if self.display.state == "countdown":
            self.display.state = "flash"
            self.display.update()
            self.timer.start(VISION_PREFLASH_MS)
            return
        if self.display.state == "flash":
            self.display.state = "showing"
            self.display.number = self.target
            self.display.update()
            self.timer.start(VISION_NUMBER_MS)
            return
        if self.display.state == "showing":
            self.display.state = "hidden"
            self.display.number = ""
            self.display.update()
            self.response_started = time.monotonic()
            self._answer_state = True
            self.answer.setEnabled(True)
            self.submit_button.setEnabled(True)
            self.answer.setFocus()
            self.status.setText("数字已经消失，请输入刚才看到的 6 位数字")

    def submit(self) -> None:
        if not self._answer_state:
            return
        entered = self.answer.text().strip()
        if len(entered) != 6:
            self.status.setText("请输入完整的 6 位数字")
            return
        response_ms = max(1, round((time.monotonic() - self.response_started) * 1000))
        success = entered == self.target
        self._answer_state = False
        self.answer.setEnabled(False)
        self.submit_button.setEnabled(False)
        self.display.state = "correct" if success else "wrong"
        self.display.update()
        self.status.setText(
            f"正确，用时 {format_duration(response_ms)}"
            if success
            else f"刚才的数字是 {self.target}"
        )
        self.history_store.add(
            TrainingRecord(
                kind="vision",
                duration_ms=response_ms,
                success=success,
                note=f"target={self.target}; entered={entered}",
            )
        )
        self._refresh_recent()

    def _refresh_recent(self) -> None:
        records = self.history_store.records("vision", limit=3)
        self.recent_label.setText(
            "最近："
            + "   ·   ".join(
                ("正确" if record.success else "错误") + f" {format_duration(record.duration_ms)}"
                for record in records
            )
            if records
            else "最近：--"
        )


__all__ = ["ReactionArena", "ReactionWindow", "SchulteWindow", "VisionDisplay", "VisionWindow"]
