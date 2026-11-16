"""「신청서 직접 작성」 창의 단체전 칸: 팀마다 종별 · 팀 이름(A·B·C…) · 자리별 이름(선봉·중견·주장·후보)."""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QGridLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from kendo_tournament.domain.written_form import TEAM_POSITIONS, TeamLine
from kendo_tournament.presentation.widgets import button, button_row

TEAM_NAMES = ("A", "B", "C", "D", "E", "F")
HEADERS = ("종별", "팀", *TEAM_POSITIONS)
NAME_WIDTH = 110


class WrittenTeamRows(QWidget):
    """팀 줄을 늘리고 줄인다. 종별은 대회 종별 표의 단체전 종별에서 고른다."""

    def __init__(self, categories: tuple[str, ...]) -> None:
        super().__init__()
        self._categories = categories
        self._rows: list[tuple[QComboBox, QComboBox, list[QLineEdit]]] = []
        self._grid = QGridLayout()
        self._grid.setHorizontalSpacing(8)
        for column, title in enumerate(HEADERS):
            header = QLabel(title)
            header.setObjectName("hint")
            self._grid.addWidget(header, 0, column)
        add, remove = button("팀 추가"), button("마지막 팀 빼기")
        add.clicked.connect(self._add_row)
        remove.clicked.connect(self._remove_row)
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.addLayout(self._grid)
        column.addLayout(button_row(add, remove))
        if categories:
            self._add_row()

    def _add_row(self) -> None:
        if not self._categories:
            return
        category, team = QComboBox(), QComboBox()
        category.addItems(self._categories)
        team.addItems(TEAM_NAMES)
        team.setCurrentIndex(min(len(self._rows), len(TEAM_NAMES) - 1))
        names = [QLineEdit() for _ in TEAM_POSITIONS]
        row = len(self._rows) + 1
        self._grid.addWidget(category, row, 0)
        self._grid.addWidget(team, row, 1)
        for offset, name in enumerate(names):
            name.setMinimumWidth(NAME_WIDTH)
            self._grid.addWidget(name, row, 2 + offset)
        self._rows.append((category, team, names))

    def _remove_row(self) -> None:
        if not self._rows:
            return
        category, team, names = self._rows.pop()
        for widget in (category, team, *names):
            self._grid.removeWidget(widget)
            widget.deleteLater()

    def values(self) -> tuple[TeamLine, ...]:
        return tuple(
            TeamLine(
                category.currentText(),
                team.currentText(),
                tuple((position, name.text()) for position, name in zip(TEAM_POSITIONS, names, strict=True)),
            )
            for category, team, names in self._rows
        )
