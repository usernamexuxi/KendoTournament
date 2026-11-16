"""책자 앞쪽(대회식순 · 대회임원 · 일정안내) 내용을 고치는 창. 틀은 그대로, 내용만 바꾼다.

대회사는 따로 고친다(greeting_dialog). 탭 순서는 책자 쪽 순서를 따르고, 칸은 제목이 붙은 표(program_rows_table)에
바로 적는다. 탭 안은 스크롤되어 칸이 화면 밖으로 밀리지 않는다.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QDialogButtonBox,
    QLabel,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from kendo_tournament.domain.program import ProgramContent
from kendo_tournament.presentation.program_rows_table import ProgramRowsTable
from kendo_tournament.presentation.screen_fit_dialog import ScreenFitDialog
from kendo_tournament.presentation.style import SPACING

SCREEN_SHARE = 0.85
MAX_WIDTH, MAX_HEIGHT = 900, 860


@dataclass(frozen=True)
class _Field:
    """columns 가 하나면 글 줄 목록(tuple[str, ...]), 둘이면 「왼쪽 | 오른쪽」 줄 목록이다."""

    name: str
    title: str
    columns: tuple[str, ...]
    hint: str = ""


TABS: tuple[tuple[str, tuple[_Field, ...]], ...] = (
    (
        "대회식순",
        (
            _Field("opening", "개회식", ("순서", "진행")),
            _Field("closing", "폐회식", ("순서", "진행")),
        ),
    ),
    ("대회임원", (_Field("officials", "대회임원", ("직책", "이름"), "이름이 여럿이면 쉼표로 나눕니다."),)),
    (
        "일정안내",
        (
            _Field("schedule", "경기 일정", ("일정", "시간")),
            _Field("match_guide", "경기 안내", ("항목", "내용")),
            _Field("guide_notes", "경기 안내 아래 ● 글", ("안내 글",)),
            _Field("courts", "경기장 배치", ("경기장", "부문"), "부문이 여럿이면 쉼표로 나눕니다."),
            _Field("court_rules", "경기장 수칙", ("수칙",), "번호는 책자에 자동으로 붙습니다."),
        ),
    ),
)


ProgramSave = Callable[[ProgramContent], None]


class ProgramEditor(ScreenFitDialog):
    """「저장」을 누르면 고친 대회식순·임원·일정 내용을 save 로 넘긴다."""

    def __init__(self, content: ProgramContent, save: ProgramSave, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("대회식순 · 대회임원 · 일정안내 고치기")
        self._save = save
        screen = self.screen().availableGeometry()
        self.resize(min(MAX_WIDTH, int(screen.width() * SCREEN_SHARE)), min(MAX_HEIGHT, int(screen.height() * SCREEN_SHARE)))
        self._tables: dict[str, tuple[ProgramRowsTable, bool]] = {}
        tabs = QTabWidget()
        for title, fields in TABS:
            tabs.addTab(self._tab(content, fields), title)
        hint = QLabel(
            "탭마다 책자 한 쪽입니다. 표는 칸을 두 번 누르거나 바로 글을 쳐서 고치고, "
            "줄을 고른 뒤 「줄 추가」를 누르면 그 아래에 빈 줄이 생깁니다."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("저장")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("취소")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(hint)
        layout.addWidget(tabs, 1)
        layout.addWidget(buttons)

    def _tab(self, content: ProgramContent, fields: tuple[_Field, ...]) -> QScrollArea:
        page = QWidget()
        page.setObjectName("page")
        column = QVBoxLayout(page)
        column.setSpacing(SPACING)
        for field in fields:
            value = getattr(content, field.name)
            single = len(field.columns) == 1
            rows = [(line,) for line in value] if single else [tuple(row) for row in value]
            table = ProgramRowsTable(field.columns, rows)
            title = QLabel(field.title)
            title.setObjectName("sectionTitle")
            column.addWidget(title)
            if field.hint:
                hint = QLabel(field.hint)
                hint.setObjectName("hint")
                column.addWidget(hint)
            column.addWidget(table)
            self._tables[field.name] = (table, single)
        column.addStretch(1)
        return _scrolled(page)

    def accept(self) -> None:
        self._save(self.result_content())
        super().accept()

    def result_content(self) -> ProgramContent:
        values = {}
        for name, (table, single) in self._tables.items():
            rows = table.values()
            values[name] = tuple(row[0] for row in rows) if single else tuple((left, right) for left, right in rows)
        return ProgramContent(**values)


def _scrolled(page: QWidget) -> QScrollArea:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)
    scroll.setWidget(page)
    return scroll
