"""Pure state helpers for the attention-training activities."""

import random
from collections.abc import Callable


class SchulteSession:
    """A 5x5 Schulte session that continuously covers the numbers 1 through 50.

    Phase one starts with a shuffled 1-25 board. A correct click replaces that
    cell with the corresponding number from 26-50. Once all cells have been
    replaced, the same board continues as phase two.
    """

    def __init__(self, rng: random.Random | None = None):
        source = rng or random.Random()
        self.cells: list[int | None] = list(range(1, 26))
        source.shuffle(self.cells)
        self.next_number = 1
        self.finished = False

    @property
    def phase(self) -> int:
        return 1 if self.next_number <= 25 else 2

    @property
    def progress(self) -> int:
        return self.next_number - 1

    def click(self, index: int) -> str:
        """Handle a cell click and return ``correct``, ``wrong`` or ``complete``."""
        if self.finished or not 0 <= index < len(self.cells):
            return "wrong"
        if self.cells[index] != self.next_number:
            return "wrong"

        completed_number = self.next_number
        self.next_number += 1
        if completed_number <= 25:
            self.cells[index] = completed_number + 25
        else:
            self.cells[index] = None

        if self.next_number > 50:
            self.finished = True
            return "complete"
        return "correct"


def format_duration(milliseconds: int | None) -> str:
    if milliseconds is None:
        return "--"
    if milliseconds < 1000:
        return f"{milliseconds} ms"
    return f"{milliseconds / 1000:.2f} 秒"


def schedule_after(parent, milliseconds: int, callback: Callable[[], None]) -> None:
    """Small indirection that keeps training windows easy to test."""
    from PySide6.QtCore import QTimer

    QTimer.singleShot(milliseconds, parent, callback)


__all__ = ["SchulteSession", "format_duration", "schedule_after"]
