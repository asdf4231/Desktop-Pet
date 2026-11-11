import pytest
from pydantic import ValidationError
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit

from shaqiu_pet.settings import (
    AppSettings,
    PetState,
    PetStateStore,
    SettingsStore,
    TrainingHistoryStore,
    TrainingRecord,
)
from shaqiu_pet.ui.settings_dialog import SettingsDialog


def test_settings_round_trip(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")
    settings = AppSettings(
        endpoint="https://api.example.com/v1/chat/completions",
        model="demo-model",
        system_prompt="Be concise",
    )

    store.save(settings)

    assert store.load() == settings


def test_settings_reject_invalid_endpoint():
    with pytest.raises(ValidationError):
        AppSettings(endpoint="api.example.com/chat")


def test_desktop_pet_defaults_match_a_fresh_install():
    settings = AppSettings()

    assert settings.pet_scale == 100
    assert settings.pet_opacity == 100
    assert settings.chattiness == "normal"
    assert settings.always_on_top is True
    assert settings.autostart is False
    assert settings.click_through is False


@pytest.mark.parametrize(
    "payload",
    [
        {"pet_scale": 10},
        {"pet_scale": 900},
        {"pet_opacity": 5},
        {"chattiness": "loud"},
    ],
)
def test_settings_reject_out_of_range_pet_options(payload):
    with pytest.raises(ValidationError):
        AppSettings(**payload)


def test_pet_state_remembers_where_it_was_left(tmp_path):
    store = PetStateStore(tmp_path / "pet_state.json")

    assert store.load().is_placed() is False

    store.save(PetState(x=640, y=980))
    state = store.load()

    assert (state.x, state.y) == (640, 980)
    assert state.is_placed() is True


def test_pet_state_survives_a_corrupt_file(tmp_path):
    path = tmp_path / "pet_state.json"
    path.write_text("{ not json", encoding="utf-8")

    assert PetStateStore(path).load().is_placed() is False


def test_settings_dialog_keeps_api_key_hidden_until_requested(qtbot):
    dialog = SettingsDialog(AppSettings(), "private-key")
    qtbot.addWidget(dialog)
    dialog.show()

    assert dialog.api_key.echoMode() == QLineEdit.EchoMode.Password
    qtbot.mouseClick(dialog.reveal_button, Qt.MouseButton.LeftButton)

    assert dialog.api_key.echoMode() == QLineEdit.EchoMode.Normal
    assert dialog.reveal_button.text() == "隐藏"


def test_settings_dialog_opens_on_the_connection_page_for_a_fresh_install(qtbot):
    from shaqiu_pet.ui.settings_dialog import PAGE_APPEARANCE, PAGE_CONNECTION

    fresh = SettingsDialog(AppSettings(), "")
    qtbot.addWidget(fresh)
    assert fresh.stack.currentIndex() == PAGE_CONNECTION

    configured = SettingsDialog(AppSettings(endpoint="https://api.example.com/v1"), "")
    qtbot.addWidget(configured)
    assert configured.stack.currentIndex() == PAGE_APPEARANCE


def test_saving_settings_does_not_reset_the_pet_preferences(qtbot):
    original = AppSettings(
        endpoint="https://api.example.com/v1",
        pet_scale=140,
        pet_opacity=75,
        chattiness="quiet",
        click_through=True,
        remember_position=False,
    )
    dialog = SettingsDialog(original, "key")
    qtbot.addWidget(dialog)
    saved = []
    dialog.saved.connect(lambda settings, api_key: saved.append(settings))

    dialog._save()

    assert len(saved) == 1
    kept = saved[0]
    assert kept.pet_scale == 140
    assert kept.pet_opacity == 75
    assert kept.chattiness == "quiet"
    assert kept.click_through is True
    assert kept.remember_position is False
    assert kept.endpoint == "https://api.example.com/v1"


def test_training_history_keeps_every_time_and_fastest_result(tmp_path):
    store = TrainingHistoryStore(tmp_path / "training_history.json")
    assert store.fastest_ms("reaction") is None

    store.add(TrainingRecord(kind="reaction", duration_ms=318))
    store.add(TrainingRecord(kind="reaction", duration_ms=274))
    store.add(TrainingRecord(kind="schulte", duration_ms=18_500))

    assert [record.duration_ms for record in store.records("reaction")] == [274, 318]
    assert store.fastest_ms("reaction") == 274
    assert store.fastest_ms("schulte") == 18_500
