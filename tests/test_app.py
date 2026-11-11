import gc
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from mochi_pet import app as pet_app


def test_main_keeps_pet_visible_for_the_application_lifetime(qtbot, monkeypatch):
    application = QApplication.instance()
    startup_state = []

    def inspect_startup():
        gc.collect()
        controller = pet_app._application_controller
        startup_state.append(controller is not None and controller.pet.isVisible())

    monkeypatch.setattr(sys, "argv", ["mochi-pet"])
    QTimer.singleShot(25, inspect_startup)
    QTimer.singleShot(50, application.quit)

    assert pet_app.main() == 0

    gc.collect()
    controller = pet_app._application_controller
    assert controller is not None
    assert startup_state == [True]
    controller.pet.close()
