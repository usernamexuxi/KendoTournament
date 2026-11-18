"""⑥ 책자 만들기 화면: 표지·대회사·넣을 문서·앞쪽 내용(식순·임원·일정)·뒤표지를 정하고, 미리보기로 확인한 뒤 PDF 로 저장한다."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from kendo_tournament.application.output_book import OutputBook
from kendo_tournament.domain.ports import BracketExporter, ExportError, InsertError
from kendo_tournament.presentation.back_cover_import import BackCoverImport
from kendo_tournament.presentation.cover_import import CoverImport
from kendo_tournament.presentation.file_dialogs import open_files, save_file
from kendo_tournament.presentation.greeting_dialog import GreetingDialog
from kendo_tournament.presentation.greeting_source_choice import GreetingSourceChoice
from kendo_tournament.presentation.photo_cover_editor import PhotoCoverEditor
from kendo_tournament.presentation.print_preview import PrintPreview
from kendo_tournament.presentation.program_editor import ProgramEditor
from kendo_tournament.presentation.style import SPACING
from kendo_tournament.presentation.widgets import button, button_row, page_layout, report_error, show_warnings, warning_label

INSERT_FILTER = "넣을 문서 (*.pdf *.docx *.hwpx *.hwp)"
INSERT_HINT = "PDF 는 원래 모양 그대로 들어갑니다. 한글·워드는 글과 표만 들어가니, 모양 그대로 넣으려면 PDF 로 저장해서 넣으세요."
PDF_EXTENSION = ".pdf"
SAVE_LABEL = "책자 PDF로 저장"
SAVE_HEIGHT = 52
INSERT_LIST_HEIGHT = 120
TEAM_MEMBERS_LABEL = "팀 상자 밑에 팀원 이름 넣기"
NATIONAL_COVER_NOTE = "전국 대회는 표지를 넣지 않습니다. 넣을 표지 파일이 있으면 아래에서 넣으세요 — 넣은 그대로 씁니다."
COVER_NOTE = (
    "기본은 참고 카탈로그의 앞·뒤표지입니다. 「표지 고치기」에서 내 사진으로 바꾸고 제목·날짜·장소·주최 글을 고칩니다. "
    "다 만든 표지 파일이 있으면 아래에서 넣으세요 — 넣은 그대로 씁니다."
)


class OutputView(QWidget):
    def __init__(self, book: OutputBook, exporter: BracketExporter, default_folder: Path) -> None:
        super().__init__()
        self._book = book
        self._exporter = exporter
        self._default_folder = default_folder
        layout = page_layout(
            self, "책자 만들기", f"표지와 앞쪽 내용을 확인하고, 다 됐으면 왼쪽 아래 「{SAVE_LABEL}」을 누르세요."
        )
        self._preview = PrintPreview()
        body = QHBoxLayout()
        body.setSpacing(SPACING + 2)
        body.addWidget(self._settings_panel(), 2)
        body.addWidget(self._preview, 3)
        layout.addLayout(body, 1)

    def _settings_panel(self) -> QWidget:
        """왼쪽 설정은 창이 낮아도 눌리지 않게 스크롤 안에 둔다 — 줄이면 단추끼리 겹친다."""
        save = button(SAVE_LABEL, primary=True)
        save.setMinimumHeight(SAVE_HEIGHT)
        save.clicked.connect(self._save)
        self._message = warning_label()
        self._cover_file = CoverImport(self._book, self.refresh)
        self._back_cover = BackCoverImport(self._book, self.refresh)
        self._greeting_source = GreetingSourceChoice(self._book, self.refresh)
        panel = QWidget()
        panel.setObjectName("page")
        column = QVBoxLayout(panel)
        column.setContentsMargins(0, 0, SPACING, 0)
        column.setSpacing(SPACING)
        column.addWidget(self._cover_box())
        column.addWidget(self._insert_box())
        column.addWidget(self._greeting_box())
        column.addWidget(self._program_box())
        column.addWidget(self._team_box())
        column.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(panel)
        scroll.setMinimumWidth(panel.minimumSizeHint().width() + scroll.verticalScrollBar().sizeHint().width())
        # 저장 단추가 스크롤 맨 밑에 있으면 운영자가 찾지 못한다. 설정을 아무리 길게 늘여도 늘 보이게 스크롤 밖 아래에 둔다.
        holder = QWidget()
        stack = QVBoxLayout(holder)
        stack.setContentsMargins(0, 0, 0, 0)
        stack.addWidget(scroll, 1)
        stack.addWidget(self._message)
        stack.addWidget(save)
        return holder

    def _insert_box(self) -> QGroupBox:
        box = QGroupBox("표지 뒤에 넣을 문서")
        inner = QVBoxLayout(box)
        hint = QLabel(INSERT_HINT)
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        self._inserts = QListWidget()
        add, up, down, remove = button("파일 추가"), button("▲"), button("▼"), button("빼기")
        add.clicked.connect(self._add_inserts)
        up.clicked.connect(lambda: self._move_insert(-1))
        down.clicked.connect(lambda: self._move_insert(1))
        remove.clicked.connect(self._remove_insert)
        self._inserts.setMinimumHeight(INSERT_LIST_HEIGHT)
        inner.addWidget(hint)
        inner.addWidget(self._inserts, 1)
        inner.addLayout(button_row(add, up, down, remove))
        return box

    def _cover_box(self) -> QGroupBox:
        box = QGroupBox("앞표지 · 뒤표지")
        self._cover_edit = button("표지 고치기")
        self._cover_edit.clicked.connect(self._edit_photo_cover)
        self._cover_note = QLabel()
        self._cover_note.setObjectName("hint")
        self._cover_note.setWordWrap(True)
        inner = QVBoxLayout(box)
        inner.addWidget(self._cover_note)
        inner.addLayout(button_row(self._cover_edit))
        inner.addWidget(self._cover_file)
        inner.addWidget(self._back_cover)
        return box

    def _edit_photo_cover(self) -> None:
        if PhotoCoverEditor(self._book, self).exec() == PhotoCoverEditor.DialogCode.Accepted:
            self.refresh()

    def _greeting_box(self) -> QGroupBox:
        box = QGroupBox("대회사")
        edit = button("대회사 고치기")
        edit.clicked.connect(self._edit_greeting)
        inner = QVBoxLayout(box)
        inner.addWidget(self._greeting_source)
        inner.addLayout(button_row(edit))
        return box

    def _program_box(self) -> QGroupBox:
        box = QGroupBox("대회식순 · 대회임원 · 일정안내")
        edit = button("식순·임원·일정 고치기")
        edit.clicked.connect(self._edit_program)
        inner = QVBoxLayout(box)
        inner.addLayout(button_row(edit))
        return box

    def _team_box(self) -> QGroupBox:
        box = QGroupBox("단체전 대진표")
        self._team_members = QCheckBox(TEAM_MEMBERS_LABEL)
        self._team_members.toggled.connect(self._set_team_members)
        inner = QVBoxLayout(box)
        inner.addWidget(self._team_members)
        return box

    def _set_team_members(self, shown: bool) -> None:
        self._book.set_team_members(shown)
        self._update_preview()

    def _edit_greeting(self) -> None:
        dialog = GreetingDialog(self._book.settings.greeting, self._book.set_greeting, self)
        if dialog.exec() == GreetingDialog.DialogCode.Accepted:
            self.refresh()

    def _edit_program(self) -> None:
        editor = ProgramEditor(self._book.settings.program, self._book.set_program, self)
        if editor.exec() == ProgramEditor.DialogCode.Accepted:
            self.refresh()

    def refresh(self) -> None:
        settings = self._book.settings
        national = self._book.is_national()
        self._cover_note.setText(NATIONAL_COVER_NOTE if national else COVER_NOTE)
        self._cover_edit.setVisible(not national)
        self._greeting_source.setVisible(national)
        self._greeting_source.refresh()
        self._cover_file.refresh()
        self._back_cover.refresh()
        self._inserts.clear()
        self._inserts.addItems([Path(path).name for path in settings.inserts])
        self._team_members.blockSignals(True)
        self._team_members.setChecked(settings.team_members)
        self._team_members.blockSignals(False)
        self._update_preview()

    def _update_preview(self) -> None:
        try:
            pages = self._book.pages()
        except (ExportError, InsertError, ValueError) as error:
            show_warnings(self._message, [str(error)])
            self._preview.show_pages([])
            return
        show_warnings(self._message, [])
        self._preview.show_pages(pages)

    def _add_inserts(self) -> None:
        paths = open_files(self, "표지 뒤에 넣을 문서", str(self._default_folder), INSERT_FILTER)
        if paths:
            self._book.add_inserts(paths)
            self.refresh()

    def _move_insert(self, step: int) -> None:
        row = self._inserts.currentRow()
        if row < 0:
            return
        self._book.move_insert(row, step)
        self.refresh()
        self._inserts.setCurrentRow(max(0, min(row + step, self._inserts.count() - 1)))

    def _remove_insert(self) -> None:
        row = self._inserts.currentRow()
        if row >= 0:
            self._book.remove_insert(row)
            self.refresh()

    def _save(self) -> None:
        default = self._default_folder / f"{self._book.file_stem()}{PDF_EXTENSION}"
        path = save_file(self, "PDF로 저장", str(default), f"PDF (*{PDF_EXTENSION})", PDF_EXTENSION)
        if path is None:
            return
        try:
            saved = self._book.export(self._exporter, path)
        except (ExportError, InsertError, ValueError, OSError) as error:
            report_error(self, error)
            return
        show_warnings(self._message, [f"저장했습니다: {saved}"])
        if hasattr(os, "startfile"):
            os.startfile(saved)
