import logging
import sys
import tempfile
from logging.handlers import RotatingFileHandler
from pathlib import Path

from platformdirs import user_log_path
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from shaqiu_pet import __version__, autostart
from shaqiu_pet.chat import ChatClient
from shaqiu_pet.settings import (
    AppSettings,
    CredentialStore,
    PetState,
    PetStateStore,
    SettingsStore,
    TrainingHistoryStore,
)
from shaqiu_pet.ui.art import shaqiu_icon
from shaqiu_pet.ui.chat_window import ChatWindow
from shaqiu_pet.ui.pet_widget import PetWidget
from shaqiu_pet.ui.settings_dialog import SettingsDialog
from shaqiu_pet.ui.theme import APP_STYLESHEET
from shaqiu_pet.ui.training import ReactionWindow, SchulteWindow, VisionWindow

LOGGER = logging.getLogger(__name__)

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def _log_directory_candidates() -> list[Path]:
    candidates = [Path(user_log_path("shaqiu", appauthor=False))]
    # tempfile.gettempdir() silently degrades to the current directory when no
    # temp location is usable; never let that drop logs into the project folder.
    fallback = Path(tempfile.gettempdir())
    if fallback.is_absolute() and fallback.resolve() != Path.cwd().resolve():
        candidates.append(fallback / "shaqiu")
    return candidates


def _log_file_handler() -> logging.Handler | None:
    """A rotating log file, falling back to the temp dir before giving up.

    A locked, read-only or otherwise unwritable log location must never stop the
    pet from starting, so every failure here degrades instead of raising.
    """
    for directory in _log_directory_candidates():
        try:
            directory.mkdir(parents=True, exist_ok=True)
            return RotatingFileHandler(
                directory / "shaqiu-pet.log",
                maxBytes=1_000_000,
                backupCount=3,
                encoding="utf-8",
            )
        except OSError:
            continue
    return None


def configure_logging() -> None:
    handler = _log_file_handler()
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        handlers=[handler] if handler is not None else [logging.NullHandler()],
    )


class DesktopPetApplication:
    def __init__(self, application: QApplication):
        self.application = application
        self.settings_store = SettingsStore()
        self.state_store = PetStateStore()
        self.credential_store = CredentialStore()
        self.training_history = TrainingHistoryStore()
        self.settings = self.settings_store.load()
        self.chat_client = ChatClient()
        self.windows: dict[str, object] = {}
        self.pet = PetWidget(self.settings)
        self.pet.open_chat.connect(self.open_chat)
        self.pet.open_schulte.connect(self.open_schulte)
        self.pet.open_reaction.connect(self.open_reaction)
        self.pet.open_vision.connect(self.open_vision)
        self.pet.open_settings.connect(self.open_settings)
        self.pet.quit_requested.connect(self.application.quit)
        self.pet.position_changed.connect(self._remember_position)
        self._create_tray_icon()
        if self.settings.remember_position:
            self.pet.place_at(self.state_store.load())
        self.pet.show()
        self.application.aboutToQuit.connect(self._remember_position)

    def _create_tray_icon(self) -> None:
        self.tray = QSystemTrayIcon(self._make_icon(), self.application)
        self.tray.setToolTip("shaqiu · 你的桌面小宠物")
        menu = QMenu()
        menu.addAction("陪我聊聊", self.open_chat)
        menu.addAction("舒尔特方格", self.open_schulte)
        menu.addAction("反应训练", self.open_reaction)
        menu.addAction("动态视力", self.open_vision)
        menu.addSeparator()
        self.click_through_action = menu.addAction("鼠标穿透")
        self.click_through_action.setCheckable(True)
        self.click_through_action.setChecked(self.settings.click_through)
        self.click_through_action.toggled.connect(self._set_click_through)
        menu.addAction("设置…", self.open_settings)
        menu.addAction("退出 shaqiu（下次见）", self.application.quit)
        self.tray.setContextMenu(menu)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    @staticmethod
    def _make_icon() -> QIcon:
        return QIcon(shaqiu_icon(64))

    def _show_window(self, name: str, factory):
        window = self.windows.get(name)
        if window is None:
            window = factory()
            self.windows[name] = window
            window.destroyed.connect(lambda _object=None, key=name: self.windows.pop(key, None))
            if isinstance(window, ChatWindow):
                window.settings_requested.connect(self.open_settings)
                window.closed.connect(self._on_chat_closed)
        window.show()
        window.raise_()
        window.activateWindow()

    def _on_chat_closed(self) -> None:
        """shaqiu notices when the conversation ends, instead of going silent."""
        self._pet_says("wave", "聊完了？我还在。")

    def _pet_says(self, action: str, message: str) -> None:
        try:
            self.pet.play_action(action, message)
        except RuntimeError:
            # The pet can already be torn down while the app is quitting.
            pass

    def open_chat(self) -> None:
        self._pet_says("happy", "好，我们聊聊。")
        self._show_window(
            "chat",
            lambda: ChatWindow(
                self.chat_client, self.settings, self.credential_store.get_api_key()
            ),
        )

    def open_schulte(self) -> None:
        self._pet_says("happy", "从 1 到 50，慢慢来。")
        self._show_window("schulte", lambda: SchulteWindow(self.training_history))

    def open_reaction(self) -> None:
        self._pet_says("surprise", "看到绿色就立刻点击。")
        self._show_window("reaction", lambda: ReactionWindow(self.training_history))

    def open_vision(self) -> None:
        self._pet_says("shy", "专注看六位数字。")
        self._show_window("vision", lambda: VisionWindow(self.training_history))

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self.credential_store.get_api_key())
        dialog.saved.connect(self._save_settings)
        dialog.exec()

    def _remember_position(self, *_args) -> None:
        if not self.settings.remember_position:
            return
        try:
            self.state_store.save(PetState(x=self.pet.x(), y=self.pet.y()))
        except RuntimeError:
            pass

    def _set_click_through(self, enabled: bool) -> None:
        if self.settings.click_through == enabled:
            return
        self.settings.click_through = enabled
        self.settings_store.save(self.settings)
        self.pet.apply_settings(self.settings)

    def _save_settings(self, settings: AppSettings, api_key: str) -> None:
        self.settings_store.save(settings)
        self.credential_store.set_api_key(api_key)
        previous_autostart = self.settings.autostart
        self.settings = settings

        if settings.autostart != previous_autostart:
            self._apply_autostart(settings.autostart)

        self.click_through_action.setChecked(settings.click_through)
        self.pet.apply_settings(settings)
        if not settings.remember_position:
            self.state_store.save(PetState())
        chat_window = self.windows.get("chat")
        if isinstance(chat_window, ChatWindow):
            chat_window.update_connection(settings, self.credential_store.get_api_key())

    def _apply_autostart(self, enabled: bool) -> None:
        if not autostart.is_supported():
            return
        if not autostart.set_enabled(enabled):
            LOGGER.warning("Unable to change the autostart entry")


_application_controller: DesktopPetApplication | None = None


def main() -> int:
    global _application_controller
    configure_logging()
    application = QApplication.instance() or QApplication(sys.argv)
    application.setApplicationName("shaqiu")
    application.setApplicationVersion(__version__)
    application.setWindowIcon(QIcon(shaqiu_icon(128)))
    application.setQuitOnLastWindowClosed(False)
    application.setStyle("Fusion")
    application.setStyleSheet(APP_STYLESHEET)
    if not QSystemTrayIcon.isSystemTrayAvailable():
        logging.getLogger(__name__).warning("System tray is unavailable; pet remains active.")
    try:
        _application_controller = DesktopPetApplication(application)
    except Exception:
        logging.getLogger(__name__).exception("Application startup failed")
        QMessageBox.critical(
            None, "shaqiu 无法启动", "启动过程中发生错误。详细信息已写入应用日志。"
        )
        return 1
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
