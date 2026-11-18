"""부문 화면 맨 위 줄: 지금 대회 종별 표가 무엇인지 보여 주고 「대회 종별 표 고치기」 단추를 둔다."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QLabel

from kendo_tournament.domain.division.category_table import TEMPLATES, CategoryTable
from kendo_tournament.presentation.widgets import button

SHOWN_LABELS = 4


class CategoryTableBar(QGroupBox):
    edit_requested = Signal()

    def __init__(self) -> None:
        super().__init__("대회 종별 표 — 요강에 나온 종별 목록")
        self._summary = QLabel()
        self._summary.setWordWrap(True)
        edit = button("대회 종별 표 고치기 (요강 읽기)")
        edit.clicked.connect(self.edit_requested.emit)
        row = QHBoxLayout(self)
        row.addWidget(self._summary, 1)
        row.addWidget(edit)

    def show_table(self, table: CategoryTable) -> None:
        name = next((name for name, template in TEMPLATES.items() if template == table), "직접 고친 표")
        shown = ", ".join(table.individual[:SHOWN_LABELS])
        more = " …" if len(table.individual) > SHOWN_LABELS else ""
        self._summary.setText(f"{name} · 개인전 {len(table.individual)}개({shown}{more}) · 단체전 {len(table.team)}개")
