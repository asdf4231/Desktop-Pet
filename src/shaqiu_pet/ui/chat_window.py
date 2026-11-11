import math
import time

from PySide6.QtCore import QObject, QRectF, QRunnable, QSize, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QFontMetrics, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from shaqiu_pet.chat import ChatClient, ChatMessage
from shaqiu_pet.settings import AppSettings, read_style_examples
from shaqiu_pet.ui.art import bubble_path, shaqiu_pixmap
from shaqiu_pet.ui.controls import PaintedButton
from shaqiu_pet.ui.palette import (
    CARD,
    CORAL,
    INK,
    LINE,
    MINT_DEEP,
    OUTLINE,
    qcolor,
    ui_font,
)

MAX_BUBBLE_TEXT_WIDTH = 336
BUBBLE_PAD_X = 15.0
BUBBLE_PAD_Y = 11.0
BUBBLE_TAIL = 7.0
BUBBLE_FONT_SIZE = 9.5

SUGGESTIONS = (
    "今天过得怎么样？",
    "陪我聊聊天吧",
    "给我讲个冷笑话",
    "我有点累了……",
)


class WorkerSignals(QObject):
    succeeded = Signal(str, bool)
    failed = Signal(str)


class ChatWorker(QRunnable):
    def __init__(self, client, settings, api_key, history, user_text, style_examples):
        super().__init__()
        self.client = client
        self.settings = settings
        self.api_key = api_key
        self.history = history
        self.user_text = user_text
        self.style_examples = style_examples
        self.signals = WorkerSignals()

    def run(self):
        try:
            reply, demo_mode = self.client.reply(
                self.settings,
                self.api_key,
                self.history,
                self.user_text,
                self.style_examples,
            )
            self.signals.succeeded.emit(reply, demo_mode)
        except RuntimeError as error:
            self.signals.failed.emit(str(error))


class MessageBubble(QFrame):
    """A single chat bubble that measures itself around its wrapped text."""

    def __init__(self, message: str, from_user: bool, tone: str | None = None):
        super().__init__()
        self.message = message
        self.from_user = from_user
        self.tone = tone or ("user" if from_user else "assistant")
        self.setObjectName(
            {"user": "userBubble", "error": "errorBubble"}.get(self.tone, "assistantBubble")
        )
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._text_width, self._text_height = self._measure()
        self.setFixedSize(
            QSize(
                int(self._text_width + 2 * BUBBLE_PAD_X + BUBBLE_TAIL + 3),
                int(self._text_height + 2 * BUBBLE_PAD_Y + 3),
            )
        )

    def _measure(self) -> tuple[float, float]:
        metrics = QFontMetrics(ui_font(BUBBLE_FONT_SIZE))
        bounds = metrics.boundingRect(
            0,
            0,
            int(MAX_BUBBLE_TEXT_WIDTH),
            4000,
            int(Qt.TextFlag.TextWordWrap),
            self.message,
        )
        width = min(float(MAX_BUBBLE_TEXT_WIDTH), max(46.0, float(bounds.width())))
        height = max(float(metrics.height()), float(bounds.height()))
        return width, height

    def _bubble_rect(self) -> QRectF:
        rect = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
        if self.from_user:
            return rect.adjusted(0, 0, -BUBBLE_TAIL, 0)
        return rect.adjusted(BUBBLE_TAIL, 0, 0, 0)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self._bubble_rect()
        tail = "right" if self.from_user else "left"
        radius = 16.0

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(qcolor(OUTLINE, 26))
        painter.drawPath(bubble_path(rect.translated(0, 2.2), radius, tail, BUBBLE_TAIL + 1))

        if self.tone == "user":
            gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
            gradient.setColorAt(0.0, qcolor("#F79A80"))
            gradient.setColorAt(1.0, qcolor(CORAL))
            pen = Qt.PenStyle.NoPen
            ink = "#FFFFFF"
        elif self.tone == "error":
            gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
            gradient.setColorAt(0.0, qcolor("#FFF4F0"))
            gradient.setColorAt(1.0, qcolor("#FDE7E0"))
            pen = QPen(qcolor("#F3CBBE"), 1.3)
            ink = "#AE4E44"
        else:
            gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
            gradient.setColorAt(0.0, qcolor(CARD))
            gradient.setColorAt(1.0, qcolor("#FFF6EC"))
            pen = QPen(qcolor(LINE), 1.3)
            ink = INK

        painter.setPen(pen)
        painter.setBrush(gradient)
        painter.drawPath(bubble_path(rect, radius, tail, BUBBLE_TAIL + 1))

        if self.tone != "user":
            painter.setPen(QPen(qcolor("#FFFFFF", 130), 1.1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(
                bubble_path(rect.adjusted(1.6, 1.5, -1.6, -1.6), radius - 1.5, tail, 0)
            )

        text_rect = QRectF(
            rect.left() + BUBBLE_PAD_X,
            rect.top() + BUBBLE_PAD_Y - 1,
            rect.width() - 2 * BUBBLE_PAD_X,
            rect.height() - 2 * BUBBLE_PAD_Y + 4,
        )
        painter.setPen(qcolor(ink))
        painter.setFont(ui_font(BUBBLE_FONT_SIZE))
        painter.drawText(
            text_rect,
            int(
                Qt.AlignmentFlag.AlignLeft
                | Qt.AlignmentFlag.AlignVCenter
                | Qt.TextFlag.TextWordWrap
            ),
            self.message,
        )


class TypingBubble(QFrame):
    """The three-dot 'shaqiu is thinking' indicator."""

    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(74, 44)
        self._started = time.monotonic()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(60)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5).adjusted(BUBBLE_TAIL, 0, 0, 0)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(qcolor(OUTLINE, 26))
        painter.drawPath(bubble_path(rect.translated(0, 2.2), 16, "left", BUBBLE_TAIL + 1))
        gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        gradient.setColorAt(0.0, qcolor(CARD))
        gradient.setColorAt(1.0, qcolor("#FFF6EC"))
        painter.setPen(QPen(qcolor(LINE), 1.3))
        painter.setBrush(gradient)
        painter.drawPath(bubble_path(rect, 16, "left", BUBBLE_TAIL + 1))

        elapsed = time.monotonic() - self._started
        painter.setPen(Qt.PenStyle.NoPen)
        for index in range(3):
            phase = elapsed * 3.6 - index * 0.55
            lift = max(0.0, math.sin(phase)) * 3.2
            alpha = 110 + int(max(0.0, math.sin(phase)) * 130)
            painter.setBrush(qcolor(MINT_DEEP, alpha))
            painter.drawEllipse(
                QRectF(rect.center().x() - 15 + index * 11, rect.center().y() - 3 - lift, 7, 7)
            )


class ChatWindow(QMainWindow):
    settings_requested = Signal()
    closed = Signal()

    def __init__(self, client: ChatClient, settings: AppSettings, api_key: str):
        super().__init__()
        self.client = client
        self.settings = settings
        self.api_key = api_key
        self.history: list[ChatMessage] = []
        self._typing_row: QWidget | None = None
        self._typing_bubble: TypingBubble | None = None
        self.setObjectName("chatWindow")
        self.setWindowTitle("shaqiu · 桌宠聊天室")
        self.resize(600, 740)
        self.setMinimumSize(480, 580)

        root = QWidget()
        root.setObjectName("chatWindow")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(root)
        root_layout.addWidget(self._make_header())

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.messages_host = QWidget()
        self.messages_host.setObjectName("chatBody")
        self.messages_layout = QVBoxLayout(self.messages_host)
        self.messages_layout.setContentsMargins(18, 20, 18, 16)
        self.messages_layout.setSpacing(14)
        self.messages_layout.addStretch(1)
        self.scroll.setWidget(self.messages_host)
        root_layout.addWidget(self.scroll, 1)

        root_layout.addWidget(self._make_suggestions())
        root_layout.addWidget(self._make_composer())
        self._set_status()
        self._add_message("我在这儿呀。今天想聊些什么？", from_user=False)

    # ------------------------------------------------------------------
    # construction
    # ------------------------------------------------------------------
    def _make_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("chatHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 16, 18, 16)
        layout.setSpacing(13)

        avatar = QLabel()
        avatar.setFixedSize(50, 50)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFFFFF, stop:1 #FFF0DC);"
            "border: 1.4px solid #F3DEC6; border-radius: 25px;"
        )
        self.header_avatar = avatar
        self._refresh_avatars()
        layout.addWidget(avatar, alignment=Qt.AlignmentFlag.AlignVCenter)

        identity = QVBoxLayout()
        identity.setSpacing(2)
        title = QLabel("shaqiu")
        title.setObjectName("chatTitle")
        self.connection_label = QLabel()
        self.connection_label.setObjectName("chatSubtitle")
        identity.addWidget(title)
        identity.addWidget(self.connection_label)
        layout.addLayout(identity, 1)

        self.settings_button = PaintedButton("设置", tone="cream", icon="gear", compact=True)
        self.settings_button.setToolTip("接口设置")
        self.settings_button.clicked.connect(self.settings_requested.emit)
        layout.addWidget(self.settings_button, alignment=Qt.AlignmentFlag.AlignVCenter)
        return header

    def _make_suggestions(self) -> QWidget:
        wrapper = QWidget()
        wrapper.setObjectName("chatBody")
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(18, 0, 18, 4)
        layout.setSpacing(7)
        self._suggestion_buttons = []
        for text in SUGGESTIONS[:3]:
            chip = QPushButton(text)
            chip.setObjectName("suggestionChip")
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.clicked.connect(lambda _checked=False, value=text: self._use_suggestion(value))
            layout.addWidget(chip)
            self._suggestion_buttons.append(chip)
        layout.addStretch(1)
        return wrapper

    def _refresh_avatars(self) -> None:
        self.header_avatar.setPixmap(shaqiu_pixmap(47, "happy"))

    def _message_avatar(self, mood: str) -> QLabel:
        avatar = QLabel()
        avatar.setFixedSize(34, 34)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setPixmap(shaqiu_pixmap(31, mood))
        avatar.setStyleSheet(
            "background: #FFF4E6; border: 1.2px solid #F3DEC6; border-radius: 17px;"
        )
        return avatar

    def _make_composer(self) -> QWidget:
        wrapper = QWidget()
        wrapper.setObjectName("chatBody")
        outer = QVBoxLayout(wrapper)
        outer.setContentsMargins(16, 6, 16, 16)
        outer.setSpacing(6)

        editor_frame = QFrame()
        editor_frame.setObjectName("composer")
        editor_layout = QHBoxLayout(editor_frame)
        editor_layout.setContentsMargins(14, 9, 9, 9)
        editor_layout.setSpacing(8)
        self.input = QPlainTextEdit()
        self.input.setPlaceholderText("和 shaqiu 说点什么……")
        self.input.setFixedHeight(60)
        self.input.setMaximumBlockCount(4)
        self.input.setFrameShape(QFrame.Shape.NoFrame)
        self.input.setStyleSheet(
            "QPlainTextEdit { border: 0; background: transparent; padding: 6px 2px; }"
        )
        self.input.installEventFilter(self)
        editor_layout.addWidget(self.input, 1)
        self.send_button = PaintedButton("发送", icon="send")
        self.send_button.setMinimumWidth(104)
        self.send_button.clicked.connect(self.send_message)
        editor_layout.addWidget(self.send_button)
        outer.addWidget(editor_frame)

        self.status = QLabel()
        self.status.setObjectName("faint")
        self.status.setContentsMargins(6, 0, 6, 0)
        outer.addWidget(self.status)
        return wrapper

    # ------------------------------------------------------------------
    # behaviour
    # ------------------------------------------------------------------
    def eventFilter(self, watched, event):
        if watched is self.input and event.type() == event.Type.KeyPress:
            key_event = event
            if key_event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if key_event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    self.input.insertPlainText("\n")
                else:
                    self.send_message()
                return True
        return super().eventFilter(watched, event)

    def _use_suggestion(self, text: str) -> None:
        self.input.setPlainText(text)
        self.send_message()

    def send_message(self) -> None:
        user_text = self.input.toPlainText().strip()
        if not user_text or not self.send_button.isEnabled():
            return
        self.input.clear()
        self._add_message(user_text, from_user=True)
        self.history.append(ChatMessage(role="user", content=user_text))
        self.send_button.setEnabled(False)
        self.status.setText("shaqiu 正在想怎么回你…")
        self._show_typing()
        worker = ChatWorker(
            self.client,
            self.settings.model_copy(deep=True),
            self.api_key,
            list(self.history[:-1]),
            user_text,
            read_style_examples(),
        )
        worker.signals.succeeded.connect(self._on_reply)
        worker.signals.failed.connect(self._on_error)
        QThreadPool.globalInstance().start(worker)

    def _on_reply(self, reply: str, demo_mode: bool) -> None:
        self._hide_typing()
        self.send_button.setEnabled(True)
        self._add_message(reply, from_user=False)
        self.history.append(ChatMessage(role="assistant", content=reply))
        self._set_status(demo_mode)

    def _on_error(self, message: str) -> None:
        self._hide_typing()
        self.send_button.setEnabled(True)
        self._add_message(message, from_user=False, tone="error")
        self.status.setText("刚才没连上，要不要去设置里看一眼？")

    def _set_status(self, demo_mode: bool | None = None) -> None:
        demo = demo_mode if demo_mode is not None else not bool(self.settings.endpoint)
        if demo:
            self.connection_label.setText("●  本地演示模式 · 在设置里连接模型")
            self.connection_label.setStyleSheet("color: #A9791F; font-size: 8pt;")
            self.status.setText("shaqiu 现在只会重复你的话，接上模型就能好好聊天啦")
        else:
            self.connection_label.setText("●  已连接模型 · 密钥由系统凭据库保护")
            self.connection_label.setStyleSheet(f"color: {MINT_DEEP}; font-size: 8pt;")
            self.status.setText("对话只会发送给你自己配置的服务")

    # ------------------------------------------------------------------
    # message plumbing
    # ------------------------------------------------------------------
    def _add_message(self, message: str, from_user: bool, tone: str | None = None) -> None:
        row_widget = QWidget()
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(9)
        bubble = MessageBubble(message, from_user, tone)

        if from_user:
            row.addStretch(1)
            row.addWidget(bubble, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        else:
            mood = "surprise" if tone == "error" else "idle"
            row.addWidget(self._message_avatar(mood), alignment=Qt.AlignmentFlag.AlignTop)
            row.addWidget(bubble, alignment=Qt.AlignmentFlag.AlignTop)
            row.addStretch(1)

        self.messages_layout.insertWidget(self.messages_layout.count() - 1, row_widget)
        self._scroll_to_bottom()

    def _show_typing(self) -> None:
        self._hide_typing()
        row_widget = QWidget()
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(9)
        self._typing_bubble = TypingBubble()
        row.addWidget(self._message_avatar("idle"), alignment=Qt.AlignmentFlag.AlignTop)
        row.addWidget(self._typing_bubble, alignment=Qt.AlignmentFlag.AlignTop)
        row.addStretch(1)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, row_widget)
        self._typing_row = row_widget
        self._scroll_to_bottom()

    def _hide_typing(self) -> None:
        if self._typing_row is not None:
            self._typing_row.setParent(None)
            self._typing_row.deleteLater()
            self._typing_row = None
        self._typing_bubble = None

    def _scroll_to_bottom(self) -> None:
        QTimer.singleShot(0, self._do_scroll_to_bottom)

    def _do_scroll_to_bottom(self) -> None:
        bar = self.scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def update_connection(self, settings: AppSettings, api_key: str) -> None:
        self.settings = settings
        self.api_key = api_key
        self._refresh_avatars()
        self._set_status()

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)


__all__ = ["ChatWindow", "MessageBubble", "TypingBubble"]
