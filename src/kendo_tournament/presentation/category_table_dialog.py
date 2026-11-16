"""대회 종별 표를 고치는 창. 틀(광명 회장기·시장기)을 고르거나 요강·신청서 파일에서 읽은 뒤, 바꿀 줄만 고친다.

종별 표가 정해지면 부문 화면의 「규칙 추가」가 이 표대로 부문을 만든다(운영자: 「요강 넣으면 그거에 맞게」).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QDialogButtonBox, QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from kendo_tournament.domain.division.category_table import TEMPLATES, CategoryTable
from kendo_tournament.domain.ports import UnsupportedFormat
from kendo_tournament.presentation.file_dialogs import open_file
from kendo_tournament.presentation.program_rows_table import ProgramRowsTable
from kendo_tournament.presentation.rule_widgets import ValueCombo
from kendo_tournament.presentation.screen_fit_dialog import ScreenFitDialog
from kendo_tournament.presentation.widgets import button, report_error

HINT = "요강·신청서·경기일정을 넣으면 그 안 신청서 양식(없으면 경기장배치 표)의 종별을 읽어 옵니다. 틀을 고른 뒤 바꿀 줄만 고쳐도 됩니다."
INDIVIDUAL_EXAMPLE = "신청서 글 그대로 적습니다. 예: 남초등 1~2학년 · 여청소년 (중,고) · 남자청년부 20~35세"
TEAM_EXAMPLE = "성별을 안 적으면 혼성입니다. 예: 초등저학년1~3학년 · 남청소년부(중,고) · 여자일반부"
CHOOSE_TEMPLATE = "틀 고르기"
SCREEN_SHARE = 0.9
MAX_WIDTH, MAX_HEIGHT = 1180, 900


class CategoryTableDialog(ScreenFitDialog):
    """「저장」을 누르면 result_table() 로 고친 표를 돌려준다. 파일 읽기는 read_file(경로 → 표, 실패하면 ValueError)로 맡긴다."""

    def __init__(self, table: CategoryTable, read_file, accepted_extensions: tuple[str, ...], parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("대회 종별 표")
        # 화면보다 크게 열면 「저장」 단추가 작업 표시줄 밑으로 숨는다(운영자 화면에서 실제로 잘렸다).
        screen = self.screen().availableGeometry()
        self.resize(min(MAX_WIDTH, int(screen.width() * SCREEN_SHARE)), min(MAX_HEIGHT, int(screen.height() * SCREEN_SHARE)))
        self._read_file = read_file
        self._accepted = accepted_extensions
        self._individual = ProgramRowsTable(("개인전 종별",), [(label,) for label in table.individual], show_header=False)
        self._team = ProgramRowsTable(("단체전 종별",), [(label,) for label in table.team], show_header=False)
        self._template = ValueCombo(((CHOOSE_TEMPLATE, None), *((name, name) for name in TEMPLATES)))
        self._template.activated.connect(self._apply_template)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("저장")
        buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName("primary")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("취소")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(self._toolbar())
        layout.addWidget(self._tables_area(), 1)
        layout.addWidget(buttons)

    def _toolbar(self) -> QFrame:
        read = button("요강·신청서에서 읽기", primary=True)
        read.clicked.connect(self._read_from_file)
        hint = QLabel(HINT)
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        bar = QFrame()
        bar.setObjectName("card")
        row = QHBoxLayout(bar)
        row.setSpacing(14)
        row.addWidget(read)
        row.addWidget(QLabel("또는"))
        row.addWidget(self._template)
        row.addWidget(hint, 1)
        return bar

    def _tables_area(self) -> QScrollArea:
        page = QWidget()
        page.setObjectName("page")
        column = QVBoxLayout(page)
        column.addWidget(_card(("개인전", INDIVIDUAL_EXAMPLE, self._individual), ("단체전", TEAM_EXAMPLE, self._team)))
        column.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(page)
        return scroll

    def _show(self, table: CategoryTable) -> None:
        self._individual.set_rows([(label,) for label in table.individual])
        self._team.set_rows([(label,) for label in table.team])

    def _apply_template(self) -> None:
        name = self._template.value()
        if name is not None:
            self._show(TEMPLATES[name])

    def _read_from_file(self) -> None:
        patterns = " ".join(f"*{ext}" for ext in self._accepted)
        path = open_file(self, "요강·신청서·경기일정에서 종별 읽기", "", f"요강·신청서·경기일정 ({patterns})")
        if path is None:
            return
        try:
            table = self._read_file(Path(path))
        except (UnsupportedFormat, ValueError, OSError) as error:
            report_error(self, error)
            return
        self._show(table)

    def result_table(self) -> CategoryTable:
        return CategoryTable(
            tuple(row[0] for row in self._individual.values()),
            tuple(row[0] for row in self._team.values()),
        )


def _card(*sections: tuple[str, str, ProgramRowsTable]) -> QFrame:
    """제목 · 예시 · 표를 한 카드 안에 이어서 쌓는다(운영자: 개인전·단체전을 굳이 띄우지 말고 이어서)."""
    card = QFrame()
    card.setObjectName("card")
    column = QVBoxLayout(card)
    column.setSpacing(8)
    for index, (title, example, table) in enumerate(sections):
        heading = QLabel(title)
        heading.setObjectName("cardTitle" if index == 0 else "cardTitleNext")
        note = QLabel(example)
        note.setObjectName("hint")
        note.setWordWrap(True)
        column.addWidget(heading)
        column.addWidget(note)
        column.addWidget(table)
    return card
