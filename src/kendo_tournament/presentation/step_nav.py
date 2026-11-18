"""단계 넘기기: 화면 아래쪽 「◀ 이전」「다음 ▶」 단추와 왼쪽 단계 목록의 진행 표시.

왼쪽 목록을 눌러야 다음 단계로 간다는 것을 운영자가 알기 어렵다. 화면을 다 보면 바로 아래에서 다음으로 넘어가게 한다.
"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QListWidget, QWidget

from kendo_tournament.application.step_progress import StepNote
from kendo_tournament.presentation.widgets import button

NAV_HEIGHT = 56


class StepNav(QWidget):
    """steps 는 단계 이름들. go 신호로 갈 단계 번호(0부터)를 보낸다."""

    go = Signal(int)

    def __init__(self, steps: Sequence[str]) -> None:
        super().__init__()
        self._steps = tuple(steps)
        self._current = 0
        self._previous = button("◀ 이전")
        self._next = button("", primary=True)
        for widget in (self._previous, self._next):
            widget.setMinimumHeight(NAV_HEIGHT)
        self._previous.clicked.connect(lambda: self.go.emit(self._current - 1))
        self._next.clicked.connect(lambda: self.go.emit(self._current + 1))
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 8, 0, 8)
        row.addWidget(self._previous)
        row.addStretch(1)
        row.addWidget(self._next)
        self.show_step(0)

    def show_step(self, index: int) -> None:
        self._current = index
        self._previous.setVisible(index > 0)
        last = index >= len(self._steps) - 1
        self._next.setVisible(not last)
        if not last:
            self._next.setText(f"다음: {self._steps[index + 1]}  ▶")


def show_step_notes(steps_list: QListWidget, names: Sequence[str], notes: Sequence[StepNote]) -> None:
    """단계 이름 밑에 진행 표시를 한 줄 붙인다. 글이 같으면 다시 쓰지 않는다(목록이 깜박이지 않게)."""
    for row, (name, note) in enumerate(zip(names, notes, strict=True)):
        text = f"{name}\n      {note}" if str(note) else name
        item = steps_list.item(row)
        if item is not None and item.text() != text:
            item.setText(text)
