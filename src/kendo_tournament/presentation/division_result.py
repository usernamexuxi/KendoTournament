"""③ 부문 화면 아래쪽: 나뉜 부문 목록과 손으로 합치기·나누기."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QAbstractItemView, QGroupBox, QLabel, QListWidget, QListWidgetItem, QVBoxLayout

from kendo_tournament.domain.division.builder import DivisionResult
from kendo_tournament.domain.division.unplaced import unplaced_lines
from kendo_tournament.domain.model import Division
from kendo_tournament.presentation.bye_panel import ByePanel
from kendo_tournament.presentation.widgets import button, button_row, show_warnings, warning_label

RESULT_MIN_HEIGHT = 220
FIX_LABEL = "빠진 선수·팀 자리 만들기"
EMPTY_RESULT = "「선수를 종별로 나누기」를 누르면 여기에 종별마다 몇 명인지 나옵니다."
EDIT_HINT = "고치려면 목록에서 종별을 누르고(여러 개는 Ctrl 을 누른 채) 아래 단추를 누르세요."


class DivisionResultBox(QGroupBox):
    merge_requested = Signal(list)
    merge_groups_requested = Signal(list)
    split_requested = Signal(list)
    fix_requested = Signal()

    def __init__(self) -> None:
        super().__init__("2. 나뉜 종별")
        self._empty = QLabel(EMPTY_RESULT)
        self._empty.setObjectName("hint")
        self._empty.setWordWrap(True)
        hint = QLabel(EDIT_HINT)
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        self._list = QListWidget()
        self._list.setObjectName("divisionResult")
        self._list.setMinimumHeight(RESULT_MIN_HEIGHT)
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        merge, split = button("고른 종별 하나로 합치기"), button("학년별로 쪼개기")
        merge.clicked.connect(lambda: self.merge_requested.emit(self.selected_labels()))
        split.clicked.connect(lambda: self.split_requested.emit(self.selected_labels()))
        self._warnings = warning_label()
        self._fix = button(FIX_LABEL, primary=True)
        self._fix.clicked.connect(self.fix_requested.emit)
        self._fix.hide()
        self._byes = ByePanel()
        self._byes.merge_requested.connect(self.merge_groups_requested.emit)
        layout = QVBoxLayout(self)
        layout.addWidget(self._empty)
        layout.addWidget(hint)
        layout.addWidget(self._list, 1)
        layout.addLayout(button_row(merge, split))
        layout.addWidget(self._warnings)
        layout.addLayout(button_row(self._fix))
        layout.addWidget(self._byes)

    def selected_labels(self) -> list[str]:
        return [item.data(Qt.ItemDataRole.UserRole) for item in self._list.selectedItems()]

    def show_divisions(self, divisions: tuple[Division, ...] | list[Division], result: DivisionResult | None) -> None:
        self._list.clear()
        for division in divisions:
            merged = "    (합쳐짐)" if len(division.rule_ids) > 1 else ""
            item = QListWidgetItem(f"{division.label}    {len(division.entries)}명{merged}")
            item.setData(Qt.ItemDataRole.UserRole, division.label)
            self._list.addItem(item)
        self._empty.setVisible(not divisions)
        show_warnings(self._warnings, _warning_lines(result))
        self._fix.setVisible(result is not None and bool(result.unassigned or result.unplaced_teams))
        self._byes.setVisible(result is not None and bool(divisions))
        if result is not None:
            self._byes.show_report(result.byes)

    def notify(self, message: str) -> None:
        show_warnings(self._warnings, [message])


def _warning_lines(result: DivisionResult | None) -> list[str]:
    if result is None:
        return []
    lines = list(result.warnings)
    if result.unassigned or result.unplaced_teams:
        lines.append(f"어느 종별에도 들지 못한 선수·팀이 있습니다. 「{FIX_LABEL}」를 누르면 들어갈 종별이 생깁니다.")
        lines += unplaced_lines(result)
    if result.multi_assigned:
        lines.append(f"두 종별 이상에 든 선수 {len(result.multi_assigned)}명 — 기준의 학년 범위가 겹치는지 확인해 주세요.")
    return lines
