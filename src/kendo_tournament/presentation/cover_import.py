"""「앞표지 · 뒤표지」 묶음 안의 앞표지 파일 칸: 누가 만들어 온 표지 파일을 앞표지로 그대로 쓰거나 뺀다."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from kendo_tournament.application.output_book import OutputBook
from kendo_tournament.domain.ports import InsertError
from kendo_tournament.presentation.file_dialogs import open_file
from kendo_tournament.presentation.widgets import button, button_row, report_error

COVER_FILTER = "앞표지 (*.pdf *.png *.jpg *.jpeg)"
NOT_USED = "앞표지 파일: 없음 — 사진 표지를 씁니다."
NATIONAL_NOT_USED = "앞표지 파일: 없음 — 전국 대회라 앞표지를 넣지 않습니다."
IN_USE = "앞표지 파일: {name}\n넣은 그대로 씁니다(사진 표지의 글은 얹지 않습니다)."


class CoverImport(QWidget):
    def __init__(self, book: OutputBook, changed: Callable[[], None]) -> None:
        super().__init__()
        self._book = book
        self._changed = changed
        self._state = QLabel()
        self._state.setObjectName("hint")
        self._state.setWordWrap(True)
        pick = button("앞표지 파일 넣기")
        pick.clicked.connect(self._pick)
        self._remove = button("빼기")
        self._remove.clicked.connect(self._stop)
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(6)
        column.addWidget(self._state)
        column.addLayout(button_row(pick, self._remove))

    def refresh(self) -> None:
        current = self._book.settings.cover_file
        if current:
            self._state.setText(IN_USE.format(name=Path(current).name))
        else:
            self._state.setText(NATIONAL_NOT_USED if self._book.is_national() else NOT_USED)
        self._remove.setEnabled(bool(current))

    def _pick(self) -> None:
        path = open_file(self, "앞표지 파일", str(Path.home()), COVER_FILTER)
        if path is None:
            return
        try:
            self._book.use_cover_file(path)
        except InsertError as error:
            report_error(self, error)
            return
        self._changed()

    def _stop(self) -> None:
        self._book.stop_cover_file()
        self._changed()
