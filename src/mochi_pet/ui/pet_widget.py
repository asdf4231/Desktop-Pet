import math
import random
import time
from collections.abc import Callable
from typing import NamedTuple

from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QAction,
    QCursor,
    QFont,
    QFontMetrics,
    QGuiApplication,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QMenu, QWidget

from mochi_pet.settings import AppSettings, PetState
from mochi_pet.ui.art import bubble_path, paint_mochi
from mochi_pet.ui.palette import (
    CARD,
    CORAL_DEEP,
    GOLD,
    GOLD_DEEP,
    INK,
    INK_SOFT,
    LINE,
    MINT,
    MINT_DEEP,
    OUTLINE,
    PEACH,
    PEACH_DEEP,
    qcolor,
    ui_font,
)

# The supplied portrait is taller than the old hand-drawn mascot, so the widget
# leaves enough vertical room for the full figure and the bottom controls.
PET_WIDTH = 210
PET_HEIGHT = 286

CHOICE_ZONE = QRectF(4, 250, 202, 32)
TOOLBAR_CENTERS = (35.0, 82.0, 128.0, 175.0)
TOOLBAR_TOP = 249.0
TOOLBAR_SIZE = (38.0, 32.0)

BUBBLE_MARGIN = 4.0
BUBBLE_TEXT_PADDING = 10.0
BUBBLE_MAX_TEXT_WIDTH = PET_WIDTH - 2 * BUBBLE_MARGIN - 2 * BUBBLE_TEXT_PADDING

REVEAL_CHARS_PER_SECOND = 26.0
DOZE_AFTER_SECONDS = 150.0

# How long to wait between unprompted lines, per chattiness level.
SPEAK_GAP = {"quiet": None, "normal": (48.0, 92.0), "chatty": (22.0, 46.0)}

WANDER_SPEED = 1.6  # design px per 50 ms tick, i.e. a slow stroll
WANDER_FIRST_DELAY = (14.0, 30.0)
WANDER_GAP = (26.0, 64.0)


class Choice(NamedTuple):
    """One tappable answer offered inside the pet's speech bubble."""

    label: str
    run: Callable[[], None]
    tone: str = "peach"


class PetWidget(QWidget):
    open_chat = Signal()
    open_schulte = Signal()
    open_reaction = Signal()
    open_vision = Signal()
    open_settings = Signal()
    position_changed = Signal(int, int)

    ACTIONS = {
        "idle": "嗯，我在。",
        "happy": "今天状态不错。",
        "wave": "嗨，我在这儿。",
        "dance": "活动一下。",
        "sleep": "我先眯一会儿。",
        "surprise": "哦？",
        "cheer": "好，开始吧。",
        "shy": "……被看到了。",
    }

    MOOD_BY_ACTION = {
        "idle": "idle",
        "happy": "happy",
        "wave": "wave",
        "dance": "dance",
        "sleep": "sleep",
        "surprise": "surprise",
        "cheer": "cheer",
        "shy": "shy",
    }

    # Things the pet says on its own. Chat and attention training are offered as
    # questions you answer, never as a cold menu item.
    SMALL_TALK = (
        "已经坐了很久了，起来走两步吧。",
        "记得喝口水。",
        "今天还顺利吗？",
        "窗外天黑得早了，注意休息。",
        "需要我的时候，我一直在。",
        "别熬太晚。",
    )

    def __init__(self, settings: AppSettings | None = None):
        super().__init__()
        self._settings = settings or AppSettings()
        self._scale = self._settings.pet_scale / 100.0

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self._apply_window_flags()
        self.resize(self._scaled_size())
        self.setWindowOpacity(max(0.05, self._settings.pet_opacity / 100.0))

        self._started_at = time.monotonic()
        self._hovered = False
        self._drag_anchor: QPoint | None = None
        self._window_anchor: QPoint | None = None
        self._moved_while_pressed = False

        self._message = ""
        self._message_started = 0.0
        self._message_until = 0.0
        self._choices: tuple[Choice, ...] = ()
        self._hover_choice: int | None = None
        self._hover_chip: int | None = None

        self._action = "idle"
        self._action_started = time.monotonic()
        self._action_duration = 0.0
        self._interaction_index = 0
        self._interactions = ("wave", "happy", "surprise", "dance", "shy")

        self._last_interaction = time.monotonic()
        self._next_speak_at = time.monotonic() + 5.0
        self._speak_index = 0
        self._dozing = False
        self._greeted = False

        self._wander_target: float | None = None
        self._next_wander_at = time.monotonic() + random.uniform(*WANDER_FIRST_DELAY)
        self._walking = False

        self._frame_timer = QTimer(self)
        self._frame_timer.timeout.connect(self.update)
        self._frame_timer.start(30)
        self._talk_timer = QTimer(self)
        self._talk_timer.timeout.connect(self._on_talk_tick)
        self._talk_timer.start(1000)
        self._wander_timer = QTimer(self)
        self._wander_timer.timeout.connect(self._on_wander_tick)
        self._wander_timer.start(50)

        self._position_near_corner()

    # ------------------------------------------------------------------
    # configuration
    # ------------------------------------------------------------------
    @property
    def settings(self) -> AppSettings:
        return self._settings

    def _scaled_size(self) -> QSize:
        return QSize(
            max(1, round(PET_WIDTH * self._scale)),
            max(1, round(PET_HEIGHT * self._scale)),
        )

    def _apply_window_flags(self) -> None:
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self._settings.always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        if self._settings.click_through:
            flags |= Qt.WindowType.WindowTransparentForInput
        was_visible = self.isVisible()
        self.setWindowFlags(flags)
        if was_visible:
            self.show()

    def apply_settings(self, settings: AppSettings, *, reposition: bool = True) -> None:
        """Apply a whole settings object, keeping the pet where it stands."""
        previous_scale = self._scale
        self._settings = settings
        self._scale = settings.pet_scale / 100.0

        self.setWindowOpacity(max(0.05, settings.pet_opacity / 100.0))
        self._apply_window_flags()

        if abs(self._scale - previous_scale) > 1e-6:
            # Keep the character's feet anchored while the window resizes.
            anchor_x = self.x() + self.width() / 2.0
            anchor_y = self.y() + self.height()
            self.resize(self._scaled_size())
            if reposition:
                self.move(round(anchor_x - self.width() / 2.0), round(anchor_y - self.height()))

        if not settings.wander or settings.smart_move:
            self._wander_target = None
            self._walking = False

        if settings.chattiness == "quiet":
            self._message_until = 0.0
            self._choices = ()
        self.update()

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    @property
    def current_action(self) -> str:
        return self._action

    @property
    def choice_labels(self) -> tuple[str, ...]:
        return tuple(choice.label for choice in self._choices)

    def place_at(self, state: PetState) -> None:
        """Restore a remembered position, if it still lands on a visible screen."""
        if not state.is_placed():
            return
        point = QPoint(int(state.x), int(state.y))
        for screen in QGuiApplication.screens():
            if screen.availableGeometry().contains(point):
                self.move(point)
                return

    def play_action(self, action: str, message: str | None = None) -> None:
        self._start_action(action)
        self.speak(message or self.ACTIONS[action], duration=min(self._action_duration, 3.0))

    def _start_action(self, action: str) -> None:
        if action not in self.ACTIONS:
            raise ValueError(f"Unknown pet action: {action}")
        self._action = action
        self._action_started = time.monotonic()
        self._action_duration = 4.2 if action == "sleep" else 2.6
        self.update()

    def speak(
        self,
        message: str,
        *,
        duration: float | None = None,
        choices: tuple[Choice, ...] = (),
    ) -> None:
        """Show a speech bubble, optionally with tappable answers."""
        now = time.monotonic()
        self._message = message
        self._message_started = now
        self._choices = choices
        self._hover_choice = None
        if duration is None:
            duration = min(9.0, 2.6 + len(message) * 0.12 + (2.4 if choices else 0.0))
        if choices:
            duration = max(duration, 14.0)
        self._message_until = now + duration
        self._next_speak_at = now + self._speak_gap()
        self.update()

    def _speak_gap(self) -> float:
        window = SPEAK_GAP.get(self._settings.chattiness, SPEAK_GAP["normal"])
        if window is None:
            return float("inf")
        return random.uniform(*window)

    # ------------------------------------------------------------------
    # proactive companionship
    # ------------------------------------------------------------------
    def _on_talk_tick(self) -> None:
        now = time.monotonic()
        if self._choices:
            return
        idle_for = now - self._last_interaction
        if self._settings.doze and idle_for >= DOZE_AFTER_SECONDS and not self._dozing:
            self._dozing = True
            self.play_action("sleep", "我眯一会儿，有事叫我。")
            return
        if self._dozing or now < self._next_speak_at:
            return
        self._proactive()

    def _proactive(self) -> None:
        """Mochi starts the conversation on its own."""
        if self._settings.chattiness == "quiet":
            self._next_speak_at = float("inf")
            return
        self._speak_index += 1
        beat = self._speak_index % 3
        if not self._greeted:
            self._greeted = True
            self.play_action("wave", "我是 Mochi。今天也一起待着吧。")
            # Greet first, then follow up with the play invitation shortly after.
            self._speak_index = 0
            self._next_speak_at = time.monotonic() + 16.0
            return
        if beat == 1:
            self.invite_to_play()
        elif beat == 2:
            self.speak(random.choice(self.SMALL_TALK))
        else:
            self.invite_to_chat()

    def invite_to_play(self) -> None:
        """Ask whether the user wants an attention-training round."""
        self._start_action("happy")
        self.speak(
            "要不要训练一下注意力？",
            choices=(
                Choice("舒尔特", self._accept_schulte, "gold"),
                Choice("反应", self._accept_reaction, "coral"),
                Choice("视力", self._accept_vision, "mint"),
                Choice("下次吧", self._decline, "plain"),
            ),
            duration=18.0,
        )

    def invite_to_chat(self) -> None:
        """Ask whether the user wants to talk, offering chat as an answer."""
        self._start_action("shy")
        self.speak(
            "想聊会儿天吗？",
            choices=(
                Choice("好啊", self._accept_chat, "peach"),
                Choice("待会儿", self._decline, "plain"),
            ),
            duration=18.0,
        )

    def _accept_chat(self) -> None:
        self._dismiss_choices()
        self.open_chat.emit()

    def _accept_schulte(self) -> None:
        self._dismiss_choices()
        self.open_schulte.emit()

    def _accept_reaction(self) -> None:
        self._dismiss_choices()
        self.open_reaction.emit()

    def _accept_vision(self) -> None:
        self._dismiss_choices()
        self.open_vision.emit()

    def _decline(self) -> None:
        self._dismiss_choices()
        self.play_action("shy", "好，那我等你。")

    def _dismiss_choices(self) -> None:
        self._choices = ()
        self._hover_choice = None
        self._message_until = min(self._message_until, time.monotonic() + 2.0)
        self.update()

    def react(self) -> None:
        action = self._interactions[self._interaction_index % len(self._interactions)]
        self._interaction_index += 1
        self.play_action(action)

    def _wake(self) -> None:
        self._last_interaction = time.monotonic()
        if self._dozing:
            self._dozing = False
            self.play_action("surprise", "啊，我在。")

    # ------------------------------------------------------------------
    # strolling along the desktop
    # ------------------------------------------------------------------
    def _screen_area(self):
        screen = self.screen()
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        return screen.availableGeometry() if screen is not None else None

    def _wandering_allowed(self) -> bool:
        if not self._settings.wander or self._settings.smart_move:
            return False
        if self._drag_anchor is not None or self._choices:
            return False
        return self._screen_area() is not None

    def _start_stroll(self) -> None:
        area = self._screen_area()
        if area is None:
            return
        margin = 8
        left = area.left() + margin
        right = area.right() - self.width() - margin
        if right <= left:
            return
        current = self.x()
        candidates = [left, right, random.uniform(left, right)]
        targets = [value for value in candidates if abs(value - current) > 40]
        self._wander_target = random.choice(targets or candidates)
        self._walking = True

    def _on_wander_tick(self) -> None:
        now = time.monotonic()
        if not self._wandering_allowed():
            if self._walking:
                self._walking = False
                self._wander_target = None
                self._next_wander_at = now + random.uniform(*WANDER_GAP)
                self.update()
            return

        if self._wander_target is None:
            if self._dozing or now < self._next_wander_at:
                return
            self._start_stroll()
            return

        delta = self._wander_target - self.x()
        if abs(delta) <= WANDER_SPEED:
            self.move(round(self._wander_target), self.y())
            self._wander_target = None
            self._walking = False
            self._next_wander_at = time.monotonic() + random.uniform(*WANDER_GAP)
            self.position_changed.emit(self.x(), self.y())
            self.update()
            return
        self.move(round(self.x() + math.copysign(WANDER_SPEED, delta)), self.y())

    # ------------------------------------------------------------------
    # geometry (all in design units)
    # ------------------------------------------------------------------
    def _position_near_corner(self) -> None:
        area = self._screen_area()
        if area is not None:
            self.move(area.right() - self.width() - 22, area.bottom() - self.height() - 28)

    def _to_design(self, point: QPointF) -> QPointF:
        scale = self._scale or 1.0
        return QPointF(point.x() / scale, point.y() / scale)

    def _revealed_text(self, now: float) -> str:
        if not self._message:
            return ""
        shown = int(max(0.0, now - self._message_started) * REVEAL_CHARS_PER_SECOND)
        if shown >= len(self._message):
            return self._message
        return self._message[:shown]

    def _bubble_metrics(self) -> tuple[QRectF, QRectF]:
        """Return (bubble rect, text rect) for the current message."""
        font = ui_font(9)
        metrics = QFontMetrics(font)
        bounds = metrics.boundingRect(
            0,
            0,
            int(BUBBLE_MAX_TEXT_WIDTH),
            400,
            int(Qt.TextFlag.TextWordWrap),
            self._message or " ",
        )
        text_width = min(BUBBLE_MAX_TEXT_WIDTH, max(58.0, float(bounds.width())))
        text_height = max(15.0, float(bounds.height()))
        bubble_width = text_width + 2 * BUBBLE_TEXT_PADDING
        bubble_height = text_height + 12.0
        bubble = QRectF(
            (PET_WIDTH - bubble_width) / 2.0,
            BUBBLE_MARGIN,
            bubble_width,
            bubble_height,
        )
        text = QRectF(
            bubble.left() + BUBBLE_TEXT_PADDING,
            bubble.top() + 6.0,
            text_width,
            text_height,
        )
        return bubble, text

    def _character_rect(self, bubble: QRectF) -> QRectF:
        return QRectF(5.0, 7.0, float(PET_WIDTH - 10), float(PET_HEIGHT - 21))

    def _choice_rects(self) -> list[QRectF]:
        count = len(self._choices)
        if not count:
            return []
        gap = 5.0
        each = (CHOICE_ZONE.width() - gap * (count - 1)) / count
        return [
            QRectF(
                CHOICE_ZONE.left() + index * (each + gap),
                CHOICE_ZONE.top(),
                each,
                CHOICE_ZONE.height(),
            )
            for index in range(count)
        ]

    @staticmethod
    def _toolbar_rects() -> list[QRectF]:
        width, height = TOOLBAR_SIZE
        return [
            QRectF(center - width / 2.0, TOOLBAR_TOP, width, height) for center in TOOLBAR_CENTERS
        ]

    def _choice_at(self, point: QPointF) -> int | None:
        for index, rect in enumerate(self._choice_rects()):
            if rect.contains(point):
                return index
        return None

    def _chip_at(self, point: QPointF) -> int | None:
        if self._choices:
            return None
        for index, rect in enumerate(self._toolbar_rects()):
            if rect.contains(point):
                return index
        return None

    # ------------------------------------------------------------------
    # events
    # ------------------------------------------------------------------
    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._hover_choice = None
        self._hover_chip = None
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._wake()
        pointer = self._to_design(event.position())
        index = self._choice_at(pointer)
        if index is not None:
            self._choices[index].run()
            return
        chip = self._chip_at(pointer)
        if chip is not None:
            self._run_chip(chip)
            return
        self._wander_target = None
        self._walking = False
        self._drag_anchor = event.globalPosition().toPoint()
        self._window_anchor = self.pos()
        self._moved_while_pressed = False

    def mouseMoveEvent(self, event):
        if self._drag_anchor is not None and event.buttons() & Qt.MouseButton.LeftButton:
            offset = event.globalPosition().toPoint() - self._drag_anchor
            if offset.manhattanLength() >= 5:
                self._moved_while_pressed = True
            self.move(self._window_anchor + offset)
            return
        pointer = self._to_design(event.position())
        hover_choice = self._choice_at(pointer)
        hover_chip = self._chip_at(pointer)
        if hover_choice != self._hover_choice or hover_chip != self._hover_chip:
            self._hover_choice = hover_choice
            self._hover_chip = hover_chip
            self.setCursor(
                Qt.CursorShape.PointingHandCursor
                if (hover_choice is not None or hover_chip is not None)
                else Qt.CursorShape.ArrowCursor
            )
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._drag_anchor is not None:
            if not self._moved_while_pressed:
                self.react()
            else:
                self.position_changed.emit(self.x(), self.y())
            self._drag_anchor = None
            self._window_anchor = None
            self._next_wander_at = time.monotonic() + random.uniform(*WANDER_GAP)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._wake()
            self.play_action("happy", "双击收到，去聊天吧。")
            self.open_chat.emit()

    def _run_chip(self, index: int) -> None:
        if index == 0:
            self.open_chat.emit()
        elif index == 1:
            self.open_schulte.emit()
        elif index == 2:
            self.open_reaction.emit()
        else:
            self.open_vision.emit()

    # ------------------------------------------------------------------
    # menus (kept as a secondary route; Mochi asks first)
    # ------------------------------------------------------------------
    def _show_context_menu(self, position: QPoint) -> None:
        self._wake()
        menu = QMenu(self)
        chat_action = QAction("陪我聊聊", menu)
        chat_action.triggered.connect(self.open_chat.emit)
        menu.addAction(chat_action)
        play_menu = menu.addMenu("来训练")
        for label, signal in (
            ("舒尔特方格", self.open_schulte),
            ("反应训练", self.open_reaction),
            ("动态视力", self.open_vision),
        ):
            action = QAction(label, play_menu)
            action.triggered.connect(signal.emit)
            play_menu.addAction(action)
        self._add_action_menu(menu)
        menu.addSeparator()
        settings_action = menu.addAction("设置")
        settings_action.triggered.connect(self.open_settings.emit)
        menu.exec(position)

    def _show_action_menu(self, position: QPoint) -> None:
        menu = QMenu(self)
        self._add_action_menu(menu)
        menu.exec(position)

    def _add_action_menu(self, parent: QMenu) -> None:
        action_menu = parent.addMenu("让 Mochi 做点什么")
        for action, label in (
            ("wave", "挥挥手"),
            ("happy", "开心一下"),
            ("dance", "动一动"),
            ("surprise", "惊讶"),
            ("shy", "害羞"),
            ("sleep", "打个盹"),
        ):
            command = QAction(label, action_menu)
            command.triggered.connect(lambda _checked=False, name=action: self.play_action(name))
            action_menu.addAction(command)

    # ------------------------------------------------------------------
    # painting
    # ------------------------------------------------------------------
    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(self._scale, self._scale)

        now = time.monotonic()
        elapsed = now - self._started_at
        action_elapsed = now - self._action_started
        if self._action != "idle" and action_elapsed >= self._action_duration:
            self._action = "idle"

        speaking = now < self._message_until or bool(self._choices)
        if speaking:
            bubble, _text_rect = self._bubble_metrics()
        else:
            bubble = QRectF(BUBBLE_MARGIN, BUBBLE_MARGIN, PET_WIDTH - 2 * BUBBLE_MARGIN, 0.0)
        character = self._character_rect(bubble)

        bob = self._motion_bob(elapsed, action_elapsed)
        pointer = self._to_design(self.mapFromGlobal(QCursor.pos()).toPointF())
        painter.save()
        painter.translate(0.0, bob)
        paint_mochi(
            painter,
            character,
            mood=self._current_mood(),
            time=elapsed,
            gesture=action_elapsed,
            gaze=max(-2.6, min(2.6, (pointer.x() - PET_WIDTH / 2.0) / 30.0)),
            blink=self._should_blink(elapsed, now),
        )
        painter.restore()

        if speaking:
            self._paint_bubble(painter, now)
            if self._choices:
                self._paint_choices(painter)
            elif self._hovered:
                self._paint_toolbar(painter)
        elif self._hovered:
            self._paint_toolbar(painter)

    def _current_mood(self) -> str:
        if self._dozing:
            return "sleep"
        if self._choices:
            return "shy"
        if self._walking and self._action == "idle":
            return "happy"
        return self.MOOD_BY_ACTION.get(self._action, "idle")

    def _should_blink(self, elapsed: float, now: float) -> bool:
        if self._action != "idle" or self._dozing:
            return False
        return (elapsed % 4.6) > 4.42 or (now - self._message_started) < 0.12

    def _motion_bob(self, elapsed: float, action_elapsed: float) -> float:
        if self._dozing:
            return math.sin(elapsed * 1.35) * 1.2
        if self._action == "sleep":
            return math.sin(elapsed * 1.45) * 1.1
        if self._action == "happy":
            return -abs(math.sin(action_elapsed * 9)) * 6.5
        if self._action == "dance":
            return math.sin(action_elapsed * 12) * 5
        if self._action == "cheer":
            return -abs(math.sin(action_elapsed * 8)) * 7.5
        if self._action == "surprise":
            return -max(0.0, 1 - action_elapsed * 2.4) * 9
        if self._walking:
            return -abs(math.sin(elapsed * 7.5)) * 2.4
        amplitude = 2.6 if (self._hovered or self._choices) else 1.8
        return math.sin(elapsed * 2.25) * amplitude

    def _paint_bubble(self, painter: QPainter, now: float) -> None:
        bubble, text_rect = self._bubble_metrics()
        tail = "bottom"

        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(qcolor("#3A3348", 30))
        painter.drawPath(bubble_path(bubble.translated(0, 2.5), 15, tail))
        painter.restore()

        painter.save()
        gradient = QLinearGradient(bubble.topLeft(), bubble.bottomLeft())
        gradient.setColorAt(0.0, qcolor(CARD))
        gradient.setColorAt(1.0, qcolor("#FBF4EC"))
        painter.setPen(QPen(qcolor(LINE), 1.4))
        painter.setBrush(gradient)
        painter.drawPath(bubble_path(bubble, 15, tail, tail_size=8.0))
        painter.restore()

        painter.save()
        painter.setFont(ui_font(9))
        painter.setPen(qcolor(INK))
        painter.drawText(
            text_rect,
            int(
                Qt.AlignmentFlag.AlignLeft
                | Qt.AlignmentFlag.AlignVCenter
                | Qt.TextFlag.TextWordWrap
            ),
            self._revealed_text(now),
        )
        painter.restore()

    def _paint_choices(self, painter: QPainter) -> None:
        tones = {
            "peach": (PEACH, PEACH_DEEP, "#FFFFFF"),
            "gold": (GOLD, GOLD_DEEP, "#5A3F12"),
            "mint": (MINT, MINT_DEEP, "#FFFFFF"),
            "plain": ("#EFE7DC", "#DFD3C4", INK_SOFT),
        }
        for index, (rect, choice) in enumerate(
            zip(self._choice_rects(), self._choices, strict=True)
        ):
            top, bottom, ink = tones.get(choice.tone, tones["peach"])
            hovered = index == self._hover_choice
            body = rect.translated(0, -1.5) if hovered else rect
            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(qcolor(OUTLINE, 34))
            painter.drawRoundedRect(body.translated(0, 2.0), 13, 13)
            gradient = QLinearGradient(body.topLeft(), body.bottomLeft())
            gradient.setColorAt(0.0, qcolor(top))
            gradient.setColorAt(1.0, qcolor(bottom))
            painter.setBrush(gradient)
            painter.drawRoundedRect(body, 13, 13)
            painter.setPen(qcolor(ink))
            painter.setFont(ui_font(8.5, QFont.Weight.Bold))
            label = QFontMetrics(ui_font(8.5)).elidedText(
                choice.label, Qt.TextElideMode.ElideRight, int(body.width() - 10)
            )
            painter.drawText(body, Qt.AlignmentFlag.AlignCenter, label)
            painter.restore()

    def _paint_toolbar(self, painter: QPainter) -> None:
        specs = (
            ("chat", MINT, MINT_DEEP),
            ("grid", GOLD, GOLD_DEEP),
            ("reaction", PEACH, CORAL_DEEP),
            ("eye", "#B7A9EA", "#7E6BC4"),
        )
        for index, (rect, (icon, top, bottom)) in enumerate(
            zip(self._toolbar_rects(), specs, strict=True)
        ):
            hovered = index == self._hover_chip
            body = rect.translated(0, -2.0 if hovered else 0.0)
            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(qcolor(OUTLINE, 30))
            painter.drawRoundedRect(body.translated(0, 2.5), 12, 12)
            gradient = QLinearGradient(body.topLeft(), body.bottomLeft())
            gradient.setColorAt(0.0, qcolor("#FFFFFF", 244))
            gradient.setColorAt(1.0, qcolor("#FBF1E5", 244))
            painter.setBrush(gradient)
            painter.drawRoundedRect(body, 12, 12)
            badge = QLinearGradient(body.topLeft(), body.bottomLeft())
            badge.setColorAt(0.0, qcolor(top))
            badge.setColorAt(1.0, qcolor(bottom))
            painter.setBrush(badge)
            painter.drawEllipse(QRectF(body.center().x() - 10.5, body.center().y() - 10.5, 21, 21))
            self._paint_chip_icon(painter, icon, body.center(), hovered)
            painter.restore()

    @staticmethod
    def _paint_chip_icon(painter: QPainter, icon: str, center: QPointF, hovered: bool) -> None:
        painter.save()
        painter.translate(center)
        ink = qcolor("#FFFFFF" if not hovered else "#FFFDF8")
        if icon == "chat":
            painter.setPen(QPen(ink, 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(-6.5, -5.5, 13, 9.5), 3.2, 3.2)
            painter.drawLine(QPointF(-1.5, 4.2), QPointF(-3.6, 7.0))
        elif icon == "grid":
            painter.setPen(QPen(ink, 1.45, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for offset in (-4.0, 0.0, 4.0):
                painter.drawLine(QPointF(offset, -5.5), QPointF(offset, 5.5))
                painter.drawLine(QPointF(-5.5, offset), QPointF(5.5, offset))
        elif icon == "reaction":
            painter.setPen(QPen(ink, 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(0, 0), 6.6, 6.6)
            bolt = QPainterPath(QPointF(1.0, -5.0))
            bolt.lineTo(-2.4, 0.3)
            bolt.lineTo(0.2, 0.3)
            bolt.lineTo(-1.0, 5.1)
            bolt.lineTo(3.2, -1.1)
            bolt.lineTo(0.5, -1.1)
            bolt.closeSubpath()
            painter.setBrush(ink)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(bolt)
        else:
            painter.setPen(QPen(ink, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            eye = QPainterPath(QPointF(-7.0, 0))
            eye.quadTo(QPointF(0, -6.5), QPointF(7.0, 0))
            eye.quadTo(QPointF(0, 6.5), QPointF(-7.0, 0))
            painter.drawPath(eye)
            painter.setBrush(ink)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(0, 0), 2.2, 2.2)
        painter.restore()


__all__ = ["Choice", "PetWidget"]
