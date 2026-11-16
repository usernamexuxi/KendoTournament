"""부문 화면에서 쓰는 입력 부품: 값 콤보 상자와 「빠른 설정」 상자."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QCheckBox, QComboBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel

from kendo_tournament.domain.division.presets import PresetChoice
from kendo_tournament.domain.model import ALL_GRADES, Event, Gender
from kendo_tournament.presentation.widgets import button

GENDER_CHOICES = (("남자", Gender.MALE), ("여자", Gender.FEMALE), ("혼성", None))
EVENT_CHOICES = tuple((event.value, event) for event in Event)
GRADE_CHOICES = tuple((grade.label, grade) for grade in ALL_GRADES)
MINIMUM_CHOICES = (("없음", None), *((f"{n}명 미만", n) for n in range(2, 17)))


def _key(value) -> str:
    """콤보 상자에는 파이썬 객체 대신 글자 키를 넣는다(Qt 가 객체 비교를 못 해 findData 가 실패한다)."""
    if value is None:
        return "-"
    return f"{type(value).__name__}:{getattr(value, 'name', None) or getattr(value, 'value', value)}"


class ValueCombo(QComboBox):
    """보여 줄 글자와 실제 값을 짝지은 콤보 상자. 화살표 칸 대신 목록에서 고르게 해 누르기 쉽다."""

    def __init__(self, choices: Sequence[tuple[str, object]], selected: object = None) -> None:
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._values: dict[str, object] = {}
        for text, value in choices:
            self._values[_key(value)] = value
            self.addItem(text, _key(value))
        self.select(selected)

    def wheelEvent(self, event: QWheelEvent) -> None:
        # 표·화면을 휠로 내리다 지나가는 상자의 값이 몰래 바뀌는 사고를 막는다. 휠은 바깥 스크롤로 넘긴다.
        event.ignore()

    def value(self):
        return self._values[self.currentData()]

    def select(self, value: object) -> None:
        index = self.findData(_key(value))
        if index >= 0:
            self.setCurrentIndex(index)


PRESET_NOTE = (
    "위 「대회 종별 표」의 종별마다 규칙이 하나씩 생깁니다. 신청서에만 있는 다른 종별도 뒤에 붙습니다. "
    "표에 안 드는 선수·팀은 「부문 나누기」 뒤 「빠진 선수·팀 부문 만들기」로 넣습니다."
)


class PresetBox(QGroupBox):
    """종목과 인원 기준을 고르고 「규칙 추가」를 누르면 preset_requested 로 보낸다. 종별은 대회 종별 표가 정한다."""

    preset_requested = Signal(object)

    def __init__(self) -> None:
        super().__init__("빠른 설정 — 종별 표대로 「규칙 추가」")
        self._events = {event: QCheckBox(event.value) for event in Event}
        for checkbox in self._events.values():
            checkbox.setChecked(True)
        self._minimum = ValueCombo(MINIMUM_CHOICES)
        note = QLabel(PRESET_NOTE)
        note.setObjectName("hint")
        note.setWordWrap(True)
        add = button("규칙 추가", primary=True)
        add.clicked.connect(lambda: self.preset_requested.emit(self.choice()))
        grid = QGridLayout(self)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(10)
        grid.addWidget(QLabel("종목"), 0, 0)
        grid.addLayout(_line(*self._events.values()), 0, 1)
        options = _line(QLabel("인원이"), self._minimum, QLabel("이면 옆 학년과 합침 (혼자인 부문은 늘 합침)"))
        options.addWidget(add)
        grid.addWidget(QLabel("합치기"), 1, 0)
        grid.addLayout(options, 1, 1)
        grid.addWidget(note, 2, 1)

    def choice(self) -> PresetChoice:
        """종별 표는 화면이 대회에서 채운다(division_view)."""
        return PresetChoice(
            events=tuple(event for event, box in self._events.items() if box.isChecked()),
            min_entries=self._minimum.value(),
        )


def _line(*widgets) -> QHBoxLayout:
    line = QHBoxLayout()
    line.setSpacing(14)
    for widget in widgets:
        line.addWidget(widget)
    line.addStretch(1)
    return line
