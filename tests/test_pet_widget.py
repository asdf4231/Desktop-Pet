from PySide6.QtCore import QPoint, Qt

from mochi_pet.settings import AppSettings
from mochi_pet.ui.pet_widget import (
    PET_HEIGHT,
    PET_WIDTH,
    TOOLBAR_CENTERS,
    TOOLBAR_SIZE,
    TOOLBAR_TOP,
    PetWidget,
)


def _toolbar_point(index: int) -> QPoint:
    return QPoint(round(TOOLBAR_CENTERS[index]), round(TOOLBAR_TOP + TOOLBAR_SIZE[1] / 2))


def test_pet_widget_renders_transparent_window(qtbot):
    pet = PetWidget()
    qtbot.addWidget(pet)
    pet.show()
    qtbot.wait(80)

    image = pet.grab().toImage()

    assert image.width() == PET_WIDTH
    assert image.height() == PET_HEIGHT
    assert image.pixelColor(100, 100).alpha() > 0


def test_pet_keeps_chat_training_and_playful_reactions(qtbot):
    pet = PetWidget()
    qtbot.addWidget(pet)
    opened = []
    pet.open_chat.connect(lambda: opened.append("chat"))
    pet.open_schulte.connect(lambda: opened.append("schulte"))
    pet.open_reaction.connect(lambda: opened.append("reaction"))
    pet.open_vision.connect(lambda: opened.append("vision"))
    pet.show()

    for index in range(4):
        qtbot.mouseClick(pet, Qt.MouseButton.LeftButton, pos=_toolbar_point(index))
    pet.play_action("dance")

    assert opened == ["chat", "schulte", "reaction", "vision"]
    assert pet.current_action == "dance"


def test_pet_asks_before_opening_training(qtbot):
    pet = PetWidget()
    qtbot.addWidget(pet)
    opened = []
    pet.open_schulte.connect(lambda: opened.append("schulte"))
    pet.open_reaction.connect(lambda: opened.append("reaction"))
    pet.open_vision.connect(lambda: opened.append("vision"))
    pet.show()

    pet.invite_to_play()

    assert pet.choice_labels == ("舒尔特", "反应", "视力", "下次吧")
    assert pet.current_action == "happy"

    answer = pet._choice_rects()[0].center().toPoint()
    qtbot.mouseClick(pet, Qt.MouseButton.LeftButton, pos=answer)

    assert opened == ["schulte"]
    assert pet.choice_labels == ()


def test_pet_asks_before_opening_chat_and_accepts_a_no(qtbot):
    pet = PetWidget()
    qtbot.addWidget(pet)
    opened = []
    pet.open_chat.connect(lambda: opened.append("chat"))
    pet.show()

    pet.invite_to_chat()
    assert pet.choice_labels == ("好啊", "待会儿")

    decline = pet._choice_rects()[1].center().toPoint()
    qtbot.mouseClick(pet, Qt.MouseButton.LeftButton, pos=decline)

    assert opened == []
    assert pet.choice_labels == ()

    pet.invite_to_chat()
    accept = pet._choice_rects()[0].center().toPoint()
    qtbot.mouseClick(pet, Qt.MouseButton.LeftButton, pos=accept)

    assert opened == ["chat"]


def test_pet_does_not_interrupt_itself_while_a_question_is_open(qtbot):
    pet = PetWidget()
    qtbot.addWidget(pet)
    pet.show()

    pet.invite_to_play()
    message = pet._message
    pet._next_speak_at = 0.0

    pet._on_talk_tick()

    assert pet._message == message
    assert pet.choice_labels == ("舒尔特", "反应", "视力", "下次吧")


def test_pet_scale_resizes_the_window_and_keeps_click_targets(qtbot):
    pet = PetWidget(AppSettings(pet_scale=150))
    qtbot.addWidget(pet)
    opened = []
    pet.open_chat.connect(lambda: opened.append("chat"))
    pet.show()

    assert pet.width() == round(PET_WIDTH * 1.5)
    assert pet.height() == round(PET_HEIGHT * 1.5)

    # Click targets are authored in design units and scale with the window.
    point = _toolbar_point(0)
    qtbot.mouseClick(
        pet,
        Qt.MouseButton.LeftButton,
        pos=QPoint(round(point.x() * 1.5), round(point.y() * 1.5)),
    )

    assert opened == ["chat"]


def test_quiet_chattiness_never_speaks_first(qtbot):
    pet = PetWidget(AppSettings(chattiness="quiet"))
    qtbot.addWidget(pet)
    pet.show()

    pet._next_speak_at = 0.0
    for _ in range(4):
        pet._on_talk_tick()

    assert pet._message == ""


def test_pet_opacity_and_scale_come_from_settings(qtbot):
    pet = PetWidget(AppSettings(pet_opacity=60))
    qtbot.addWidget(pet)
    pet.show()
    pet.grab()

    assert abs(pet.windowOpacity() - 0.6) < 0.02

    pet.apply_settings(AppSettings(pet_opacity=100, pet_scale=120))

    assert pet.width() == round(PET_WIDTH * 1.2)
    assert abs(pet.windowOpacity() - 1.0) < 0.02


def test_smart_move_keeps_the_pet_put(qtbot):
    pet = PetWidget(AppSettings(wander=True, smart_move=True))
    qtbot.addWidget(pet)
    pet.show()

    pet._next_wander_at = 0.0
    for _ in range(10):
        pet._on_wander_tick()

    assert pet._wander_target is None
    assert pet._walking is False
