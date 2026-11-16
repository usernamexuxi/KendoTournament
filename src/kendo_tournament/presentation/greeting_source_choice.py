"""전국 대회의 「대회사」 쪽 고르기: 프로그램 틀로 넣기 · 빼기 · 받은 파일로 넣기(운영자 지시).

광명 대회는 늘 프로그램 틀이라 이 칸을 보이지 않는다(출력 화면이 정한다).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from kendo_tournament.application.output_book import OutputBook
from kendo_tournament.domain.book import GreetingSource
from kendo_tournament.domain.ports import InsertError
from kendo_tournament.presentation.file_dialogs import open_file
from kendo_tournament.presentation.widgets import button, button_row, report_error

GREETING_FILTER = "대회사 문서 (*.pdf *.docx *.hwpx *.hwp)"
STATE_TEXT = {
    GreetingSource.TEMPLATE: "대회사: 프로그램 틀로 넣습니다(「대회사 고치기」에서 고칩니다).",
    GreetingSource.NONE: "대회사: 넣지 않습니다.",
}


class GreetingSourceChoice(QWidget):
    def __init__(self, book: OutputBook, changed: Callable[[], None]) -> None:
        super().__init__()
        self._book = book
        self._changed = changed
        self._state = QLabel()
        self._state.setObjectName("hint")
        self._state.setWordWrap(True)
        template, none, from_file = button("틀로 넣기"), button("빼기"), button("파일로 넣기")
        template.clicked.connect(lambda: self._choose(GreetingSource.TEMPLATE))
        none.clicked.connect(lambda: self._choose(GreetingSource.NONE))
        from_file.clicked.connect(self._pick_file)
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(6)
        column.addWidget(self._state)
        column.addLayout(button_row(template, none, from_file))

    def refresh(self) -> None:
        source = self._book.greeting_source()
        if source is GreetingSource.FILE:
            self._state.setText(f"대회사: 파일로 넣습니다 — {Path(self._book.settings.greeting_file).name}")
        else:
            self._state.setText(STATE_TEXT[source])

    def _choose(self, source: GreetingSource) -> None:
        self._book.set_greeting_source(source)
        self._changed()

    def _pick_file(self) -> None:
        path = open_file(self, "대회사 파일", str(Path.home()), GREETING_FILTER)
        if path is None:
            return
        try:
            self._book.use_greeting_file(path)
        except InsertError as error:
            report_error(self, error)
            return
        self._changed()
