import random
import time

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

from mochi_pet.settings import TrainingHistoryStore
from mochi_pet.training import SchulteSession
from mochi_pet.ui.training import ReactionWindow, SchulteWindow, VisionWindow


def test_schulte_replaces_first_round_numbers_in_place_and_finishes_at_50():
    session = SchulteSession(random.Random(7))
    first_positions = {
        value: index for index, value in enumerate(session.cells) if value is not None
    }

    for expected in range(1, 51):
        index = session.cells.index(expected)
        result = session.click(index)
        if expected <= 25:
            assert session.cells[index] == expected + 25
            assert first_positions[expected] == index
        else:
            assert session.cells[index] is None
        assert result == ("complete" if expected == 50 else "correct")

    assert session.finished is True
    assert session.progress == 50
    assert sorted(value for value in session.cells if value is not None) == []


def test_schulte_window_records_completed_round(qtbot, tmp_path):
    store = TrainingHistoryStore(tmp_path / "training.json")
    window = SchulteWindow(store)
    qtbot.addWidget(window)
    window.start()
    window._started_at = time.monotonic() - 1.25
    assert window.session is not None

    for _ in range(50):
        index = window.session.cells.index(window.session.next_number)
        window._click_cell(index)

    records = store.records("schulte")
    assert len(records) == 1
    assert records[0].duration_ms >= 1200
    assert "50 / 50" in window.progress_label.text()


def test_reaction_training_records_green_click_and_fastest(qtbot, tmp_path):
    store = TrainingHistoryStore(tmp_path / "training.json")
    window = ReactionWindow(store)
    qtbot.addWidget(window)
    window.arena.state = "green"
    window.arena._green_at = time.monotonic() - 0.23

    QTest.mouseClick(window.arena, Qt.MouseButton.LeftButton, pos=QPoint(120, 120))

    records = store.records("reaction")
    assert len(records) == 1
    assert 180 <= records[0].duration_ms <= 350
    assert store.fastest_ms("reaction") == records[0].duration_ms


def test_vision_training_records_success_and_wrong_answers(qtbot, tmp_path):
    store = TrainingHistoryStore(tmp_path / "training.json")
    window = VisionWindow(store)
    qtbot.addWidget(window)

    for target, entered in (("012345", "012345"), ("654321", "111111")):
        window.target = target
        window._answer_state = True
        window.response_started = time.monotonic() - 0.4
        window.answer.setEnabled(True)
        window.submit_button.setEnabled(True)
        window.answer.setText(entered)
        window.submit()

    records = store.records("vision")
    assert [record.success for record in records] == [False, True]
    assert all(350 <= record.duration_ms <= 650 for record in records)
