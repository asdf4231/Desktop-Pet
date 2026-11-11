from pydantic import ValidationError
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QLinearGradient, QPainter
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from mochi_pet.settings import AppSettings
from mochi_pet.ui.art import mochi_pixmap
from mochi_pet.ui.controls import PaintedButton
from mochi_pet.ui.palette import LINE, qcolor

PAGE_APPEARANCE = 0
PAGE_BEHAVIOUR = 1
PAGE_CONNECTION = 2

CHATTINESS_CHOICES = (
    ("quiet", "安静 · 只在被叫到时说话"),
    ("normal", "正常 · 偶尔主动开口"),
    ("chatty", "话多 · 经常来找你"),
)


class PaintedRail(QFrame):
    """The warm branded column on the left of the settings dialog."""

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        gradient = QLinearGradient(QPointF(0, 0), QPointF(self.width() * 0.5, self.height()))
        gradient.setColorAt(0.0, qcolor("#FFF6EB"))
        gradient.setColorAt(0.55, qcolor("#FCE7D4"))
        gradient.setColorAt(1.0, qcolor("#F8D8BF"))
        painter.fillRect(self.rect(), gradient)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(qcolor("#FFFFFF", 70))
        painter.drawEllipse(QRectF(self.width() - 78, -34, 132, 132))
        painter.setBrush(qcolor("#FFFFFF", 45))
        painter.drawEllipse(QRectF(-50, self.height() - 96, 118, 118))

        painter.setPen(qcolor(LINE))
        painter.drawLine(self.width() - 1, 0, self.width() - 1, self.height())


class SettingsDialog(QDialog):
    saved = Signal(object, str)

    def __init__(self, settings: AppSettings, api_key: str, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsDialog")
        self.setWindowTitle("Mochi · 设置")
        self.resize(830, 700)
        self.setMinimumSize(760, 640)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self._settings = settings

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._make_rail())
        root.addWidget(self._make_content(settings, api_key), 1)

    # ------------------------------------------------------------------
    # rail
    # ------------------------------------------------------------------
    def _make_rail(self) -> QFrame:
        rail = PaintedRail()
        rail.setObjectName("settingsRail")
        rail.setFixedWidth(238)
        layout = QVBoxLayout(rail)
        layout.setContentsMargins(24, 26, 22, 22)
        layout.setSpacing(10)

        self.preview = QLabel()
        self.preview.setFixedSize(96, 96)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFFFFF, stop:1 #FFF0DC);"
            "border: 1.5px solid #F2D9BE; border-radius: 48px;"
        )
        self._refresh_preview()

        brand = QLabel("MOCHI · 桌宠伙伴")
        brand.setObjectName("railBrand")
        copy = QLabel("角色形象固定使用当前图片，只调整大小和相处方式。")
        copy.setObjectName("railCopy")
        copy.setWordWrap(True)

        layout.addWidget(self.preview, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addSpacing(4)
        layout.addWidget(brand)
        layout.addWidget(copy)
        layout.addSpacing(14)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self._nav_buttons: list[QPushButton] = []
        for index, label in enumerate(("形象", "行为", "接口")):
            button = QPushButton(f"   {label}")
            button.setObjectName("railNav")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, page=index: self._show_page(page))
            self.nav_group.addButton(button, index)
            self._nav_buttons.append(button)
            layout.addWidget(button)

        layout.addStretch(1)
        note = QLabel("API 密钥保存在系统凭据库，不会写进项目配置文件。")
        note.setObjectName("railNote")
        note.setWordWrap(True)
        layout.addWidget(note)
        return rail

    def _refresh_preview(self, *_args) -> None:
        if hasattr(self, "scale_slider"):
            size = min(92, max(52, int(self.scale_slider.value() * 0.62)))
        else:
            size = 92
        self.preview.setPixmap(mochi_pixmap(size, "idle"))

    def _show_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        button = self.nav_group.button(index)
        if button is not None:
            button.setChecked(True)

    # ------------------------------------------------------------------
    # content
    # ------------------------------------------------------------------
    def _make_content(self, settings: AppSettings, api_key: str) -> QWidget:
        content = QWidget()
        content.setObjectName("settingsContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 24, 32, 22)
        layout.setSpacing(0)

        header = QHBoxLayout()
        eyebrow = QLabel("PREFERENCES")
        eyebrow.setObjectName("eyebrow")
        self.connection_status = QLabel()
        self.connection_status.setObjectName("connectionStatus")
        self.connection_status.setText("已连接模型" if settings.endpoint else "本地演示模式")
        self.connection_status.setProperty("state", "live" if settings.endpoint else "demo")
        header.addWidget(eyebrow)
        header.addStretch(1)
        header.addWidget(self.connection_status)
        layout.addLayout(header)
        layout.addSpacing(12)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._make_appearance_page(settings))
        self.stack.addWidget(self._make_behaviour_page(settings))
        self.stack.addWidget(self._make_connection_page(settings, api_key))
        layout.addWidget(self.stack, 1)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #B14F46; font-size: 8.5pt;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        footer = QHBoxLayout()
        footer.setSpacing(10)
        footer.addStretch(1)
        cancel_button = PaintedButton("取消", tone="cream")
        cancel_button.setMinimumWidth(96)
        cancel_button.clicked.connect(self.reject)
        footer.addWidget(cancel_button)
        self.save_button = PaintedButton("保存设置", tone="coral")
        self.save_button.setMinimumWidth(126)
        self.save_button.clicked.connect(self._save)
        footer.addWidget(self.save_button)
        layout.addLayout(footer)

        # First run lands on the connection page; afterwards, on the character.
        self._show_page(PAGE_CONNECTION if not settings.endpoint else PAGE_APPEARANCE)
        return content

    def _make_page_header(self, title: str, subtitle: str) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        heading = QLabel(title)
        heading.setObjectName("pageTitle")
        copy = QLabel(subtitle)
        copy.setObjectName("muted")
        copy.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(copy)
        return wrapper

    # --- page 1: appearance -------------------------------------------
    def _make_appearance_page(self, settings: AppSettings) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(14)
        layout.addWidget(
            self._make_page_header(
                "形象",
                "角色图片与配色固定，不支持替换或换色；可以调整显示大小和透明度。",
            )
        )

        fixed_card = QFrame()
        fixed_card.setObjectName("softCard")
        fixed_layout = QHBoxLayout(fixed_card)
        fixed_layout.setContentsMargins(16, 14, 16, 14)
        fixed_layout.setSpacing(14)
        fixed_preview = QLabel()
        fixed_preview.setFixedSize(104, 128)
        fixed_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fixed_preview.setPixmap(mochi_pixmap(94, "idle"))
        fixed_copy = QVBoxLayout()
        fixed_title = QLabel("固定角色形象")
        fixed_title.setObjectName("sectionTitle")
        fixed_note = QLabel("原图保留，动起来时会呼吸、轻微摇摆，并对点击和动作作出反馈。")
        fixed_note.setObjectName("muted")
        fixed_note.setWordWrap(True)
        fixed_copy.addWidget(fixed_title)
        fixed_copy.addWidget(fixed_note)
        fixed_copy.addStretch(1)
        fixed_layout.addWidget(fixed_preview)
        fixed_layout.addLayout(fixed_copy, 1)
        layout.addWidget(fixed_card)

        self.scale_slider, scale_row = self._make_slider(
            "角色大小", settings.pet_scale, 60, 180, "{value}%"
        )
        self.scale_slider.valueChanged.connect(self._refresh_preview)
        layout.addWidget(scale_row)

        self.opacity_slider, opacity_row = self._make_slider(
            "不透明度", settings.pet_opacity, 30, 100, "{value}%"
        )
        layout.addWidget(opacity_row)

        self.always_on_top = QCheckBox("始终显示在其它窗口前面")
        self.always_on_top.setChecked(settings.always_on_top)
        layout.addWidget(self.always_on_top)
        layout.addStretch(1)
        return page

    def _make_slider(
        self, title: str, value: int, minimum: int, maximum: int, template: str
    ) -> tuple[QSlider, QWidget]:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        row = QHBoxLayout()
        label = QLabel(title)
        label.setObjectName("fieldLabel")
        readout = QLabel(template.format(value=value))
        readout.setObjectName("muted")
        row.addWidget(label)
        row.addStretch(1)
        row.addWidget(readout)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        slider.valueChanged.connect(lambda current: readout.setText(template.format(value=current)))
        layout.addLayout(row)
        layout.addWidget(slider)
        return slider, wrapper

    # --- page 2: behaviour --------------------------------------------
    def _make_behaviour_page(self, settings: AppSettings) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(14)
        layout.addWidget(self._make_page_header("行为", "决定它什么时候动、什么时候开口。"))

        movement = QGroupBox("行动")
        movement_layout = QVBoxLayout(movement)
        movement_layout.setContentsMargins(12, 16, 12, 10)
        movement_layout.setSpacing(2)
        self.wander = QCheckBox("允许它自己在桌面上走动")
        self.wander.setChecked(settings.wander)
        self.smart_move = QCheckBox("只有我主动互动时它才移动")
        self.smart_move.setChecked(settings.smart_move)
        self.doze = QCheckBox("长时间没人理就打个盹")
        self.doze.setChecked(settings.doze)
        movement_layout.addWidget(self.wander)
        movement_layout.addWidget(self.smart_move)
        movement_layout.addWidget(self.doze)
        layout.addWidget(movement)

        window = QGroupBox("窗口")
        window_layout = QVBoxLayout(window)
        window_layout.setContentsMargins(12, 16, 12, 10)
        window_layout.setSpacing(2)
        self.remember_position = QCheckBox("记住上次待的位置")
        self.remember_position.setChecked(settings.remember_position)
        self.click_through = QCheckBox("鼠标穿透（点击直接落到下面的窗口）")
        self.click_through.setChecked(settings.click_through)
        self.autostart = QCheckBox("开机时自动启动")
        self.autostart.setChecked(settings.autostart)
        window_layout.addWidget(self.remember_position)
        window_layout.addWidget(self.click_through)
        window_layout.addWidget(self.autostart)
        layout.addWidget(window)

        talk = QGroupBox("对话")
        talk_layout = QVBoxLayout(talk)
        talk_layout.setContentsMargins(12, 16, 12, 12)
        talk_layout.setSpacing(7)
        talk_label = QLabel("主动开口的频率")
        talk_label.setObjectName("fieldLabel")
        self.chattiness = QComboBox()
        for key, label in CHATTINESS_CHOICES:
            self.chattiness.addItem(label, key)
        index = self.chattiness.findData(settings.chattiness)
        if index >= 0:
            self.chattiness.setCurrentIndex(index)
        talk_layout.addWidget(talk_label)
        talk_layout.addWidget(self.chattiness)
        layout.addWidget(talk)
        layout.addStretch(1)
        return page

    # --- page 3: connection -------------------------------------------
    def _make_connection_page(self, settings: AppSettings, api_key: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(0)
        layout.addWidget(
            self._make_page_header("模型与人设", "告诉 Mochi 去哪里说话，以及它该怎么陪你。")
        )
        layout.addSpacing(18)

        self.endpoint = QLineEdit(settings.endpoint)
        self.endpoint.setPlaceholderText("https://api.example.com/v1/chat/completions")
        self.endpoint.setMinimumHeight(42)
        self.model = QLineEdit(settings.model)
        self.model.setPlaceholderText("例如 gpt-4o-mini")
        self.model.setMinimumHeight(42)
        self.api_key = QLineEdit(api_key)
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("粘贴 API Key")
        self.api_key.setMinimumHeight(42)
        self.reveal_button = PaintedButton("显示", tone="cream", compact=True)
        self.reveal_button.setCheckable(True)
        self.reveal_button.setFixedWidth(58)
        self.reveal_button.setMinimumHeight(42)
        self.reveal_button.toggled.connect(self._toggle_api_key_visibility)
        key_row = QHBoxLayout()
        key_row.setSpacing(8)
        key_row.addWidget(self.api_key, 1)
        key_row.addWidget(self.reveal_button)

        self.system_prompt = QPlainTextEdit(settings.system_prompt)
        self.system_prompt.setMinimumHeight(112)
        self.system_prompt.setPlaceholderText("例如：你是一只安静又可靠的桌面伙伴，说话短一点……")

        layout.addWidget(
            self._make_field("接口地址", self.endpoint, "完整的 Chat Completions 兼容接口 URL")
        )
        layout.addSpacing(13)
        layout.addWidget(self._make_field("模型名称", self.model, "按服务商要求填写模型 ID"))
        layout.addSpacing(13)

        key_field = QWidget()
        key_field_layout = QVBoxLayout(key_field)
        key_field_layout.setContentsMargins(0, 0, 0, 0)
        key_field_layout.setSpacing(6)
        key_label = QLabel("API 密钥")
        key_label.setObjectName("fieldLabel")
        key_field_layout.addWidget(key_label)
        key_field_layout.addLayout(key_row)
        layout.addWidget(key_field)
        layout.addSpacing(15)

        prompt_label = QLabel("角色设定")
        prompt_label.setObjectName("fieldLabel")
        prompt_help = QLabel("定义它的性格、语气和回复习惯。")
        prompt_help.setObjectName("helperText")
        layout.addWidget(prompt_label)
        layout.addWidget(prompt_help)
        layout.addSpacing(7)
        layout.addWidget(self.system_prompt, 1)
        return page

    @staticmethod
    def _make_field(label_text: str, field: QWidget, helper_text: str) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        label = QLabel(label_text)
        label.setObjectName("fieldLabel")
        helper = QLabel(helper_text)
        helper.setObjectName("helperText")
        layout.addWidget(label)
        layout.addWidget(field)
        layout.addWidget(helper)
        return wrapper

    # ------------------------------------------------------------------
    def _toggle_api_key_visibility(self, visible: bool) -> None:
        self.api_key.setEchoMode(
            QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
        )
        self.reveal_button.setText("隐藏" if visible else "显示")

    def _save(self) -> None:
        values = self._settings.model_dump()
        values.update(
            endpoint=self.endpoint.text(),
            model=self.model.text().strip(),
            system_prompt=self.system_prompt.toPlainText().strip(),
            pet_scale=self.scale_slider.value(),
            pet_opacity=self.opacity_slider.value(),
            always_on_top=self.always_on_top.isChecked(),
            wander=self.wander.isChecked(),
            smart_move=self.smart_move.isChecked(),
            doze=self.doze.isChecked(),
            remember_position=self.remember_position.isChecked(),
            click_through=self.click_through.isChecked(),
            autostart=self.autostart.isChecked(),
            chattiness=self.chattiness.currentData(),
        )
        try:
            settings = AppSettings(**values)
        except ValidationError as error:
            self.error_label.setText(str(error.errors()[0]["msg"]))
            return
        self.saved.emit(settings, self.api_key.text())
        self.accept()


__all__ = ["SettingsDialog"]
