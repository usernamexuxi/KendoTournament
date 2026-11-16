"""책자 앞쪽 내용 한 칸(예: 개회식 순서)을 고치는 표. 줄 추가·삭제·위아래 옮기기 단추가 붙는다.

전에는 글 칸에 「항목 | 내용」을 손으로 쳤다(운영자: 「쓰기 편하게」). 이제 칸마다 제목이 있는 표에 바로 적는다.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from kendo_tournament.presentation.widgets import TABLE_ROW_HEIGHT, button, button_row

FIRST_COLUMN_WIDTH = 230
EMPTY_ROWS_SHOWN = 1
CELL_ALIGNMENT = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter


class ProgramRowsTable(QWidget):
    """columns 가 하나면 글 한 줄짜리 목록, 둘이면 「왼쪽 | 오른쪽」 줄 목록이다. 빈 줄은 저장하지 않는다."""

    def __init__(self, columns: tuple[str, ...], rows: list[tuple[str, ...]], show_header: bool = True) -> None:
        """show_header 를 끄면 칸 제목 줄을 숨긴다 — 바깥 제목이 이미 같은 말을 할 때(종별 표)."""
        super().__init__()
        self._table = QTableWidget(0, len(columns))
        self._table.setHorizontalHeaderLabels(list(columns))
        self._table.horizontalHeader().setVisible(show_header)
        self._table.verticalHeader().setDefaultSectionSize(TABLE_ROW_HEIGHT)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        header = self._table.horizontalHeader()
        if len(columns) > 1:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
            self._table.setColumnWidth(0, FIRST_COLUMN_WIDTH)
        header.setStretchLastSection(True)
        # 표 안에 스크롤을 두지 않고 줄을 다 보인다. 창 스크롤과 표 스크롤이 겹치면 마지막 줄이 잘려 보였다(운영자: 가독성).
        self._table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        for row in rows:
            self._append(row)
        self._fit_height()
        add, remove, up, down = button("줄 추가"), button("줄 삭제"), button("위로"), button("아래로")
        add.clicked.connect(self._add_row)
        remove.clicked.connect(self._remove_row)
        up.clicked.connect(lambda: self._move(-1))
        down.clicked.connect(lambda: self._move(1))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._table)
        layout.addLayout(button_row(add, remove, up, down))

    def _append(self, values: tuple[str, ...]) -> int:
        row = self._table.rowCount()
        self._table.insertRow(row)
        for column in range(self._table.columnCount()):
            text = values[column] if column < len(values) else ""
            item = QTableWidgetItem(text)
            item.setTextAlignment(CELL_ALIGNMENT)
            self._table.setItem(row, column, item)
        return row

    def _fit_height(self) -> None:
        rows = max(EMPTY_ROWS_SHOWN, self._table.rowCount())
        frame = 2 * self._table.frameWidth()
        top = self._table.horizontalHeader()
        header = 0 if top.isHidden() else top.sizeHint().height()
        self._table.setFixedHeight(header + rows * TABLE_ROW_HEIGHT + frame)

    def _add_row(self) -> None:
        """고른 줄 바로 아래(없으면 맨 끝)에 빈 줄을 넣고 첫 칸을 바로 고칠 수 있게 한다."""
        current = self._table.currentRow()
        row = self._append(("",) * self._table.columnCount())
        self._fit_height()
        target = current + 1 if current >= 0 else row
        while row > target:
            self._swap(row, row - 1)
            row -= 1
        self._table.setCurrentCell(row, 0)
        self._table.editItem(self._table.item(row, 0))

    def _remove_row(self) -> None:
        row = self._table.currentRow()
        if row >= 0:
            self._table.removeRow(row)
            self._fit_height()

    def _move(self, step: int) -> None:
        row = self._table.currentRow()
        target = row + step
        if row < 0 or not 0 <= target < self._table.rowCount():
            return
        self._swap(row, target)
        self._table.setCurrentCell(target, self._table.currentColumn())

    def _swap(self, a: int, b: int) -> None:
        for column in range(self._table.columnCount()):
            first, second = self._table.takeItem(a, column), self._table.takeItem(b, column)
            self._table.setItem(a, column, second)
            self._table.setItem(b, column, first)

    def set_rows(self, rows: list[tuple[str, ...]]) -> None:
        self._table.setRowCount(0)
        for row in rows:
            self._append(row)
        self._fit_height()

    def values(self) -> list[tuple[str, ...]]:
        """줄마다 칸 글. 모든 칸이 빈 줄은 뺀다."""
        result = []
        for row in range(self._table.rowCount()):
            cells = tuple(self._cell(row, column) for column in range(self._table.columnCount()))
            if any(cells):
                result.append(cells)
        return result

    def _cell(self, row: int, column: int) -> str:
        item = self._table.item(row, column)
        return item.text().strip() if item is not None else ""
