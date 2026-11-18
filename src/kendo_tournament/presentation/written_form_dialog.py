"""「신청서 직접 작성」 창: 문자로 신청한 사람을 신청서 모양 그대로 적는다(운영자 지시).

개인전은 대회 종별 표의 종별마다 한 줄이고 이름을 쉼표나 띄어쓰기로 늘어놓는다. 단체전은 팀마다 자리별 이름을 적는다.
문자 글을 통째로 붙여 넣어 해석하지는 않는다(written_form 참고).
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from kendo_tournament.application.tournament_session import TournamentSession
from kendo_tournament.domain.written_form import IndividualLine, WrittenForm, entry_lines, split_names
from kendo_tournament.presentation.screen_fit_dialog import ScreenFitDialog
from kendo_tournament.presentation.style import SPACING
from kendo_tournament.presentation.written_team_rows import WrittenTeamRows

SCREEN_SHARE = 0.85
MAX_WIDTH, MAX_HEIGHT = 1000, 860
HINT = (
    "문자로 받은 신청을 신청서처럼 적습니다. 개인전은 종별 줄에 이름을 쉼표나 띄어쓰기로 늘어놓고, "
    "단체전은 팀마다 자리별로 이름을 적습니다. 같은 도장을 다시 적으면 그 도장의 직접 작성 명단이 새 내용으로 바뀝니다."
)
NAMES_PLACEHOLDER = "예: 홍길동, 김철수 이영희"
# 요강이 학년마다 따로여도 신청이 「초1~2」처럼 묶여 오면 넣을 줄이 없었다(운영자 지적). 종별 글을 직접 적는 줄을 둔다.
FREE_ROWS = 2
FREE_CATEGORY_PLACEHOLDER = "예: 남초 1~2"
FREE_TITLE = "다른 종별 직접 적기 — 위에 맞는 줄이 없을 때(성별·학년을 함께 적기)"


class WrittenFormDialog(ScreenFitDialog):
    """「저장」을 누르면 명단에 넣는다. 도장이 비었으면 알리고 창을 닫지 않는다."""

    def __init__(self, session: TournamentSession, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("신청서 직접 작성")
        self._session = session
        screen = self.screen().availableGeometry()
        self.resize(min(MAX_WIDTH, int(screen.width() * SCREEN_SHARE)), min(MAX_HEIGHT, int(screen.height() * SCREEN_SHARE)))
        categories = session.tournament.categories
        self._dojang = QComboBox()
        self._dojang.setEditable(True)
        self._dojang.addItems(session.tournament.dojang_names())
        self._dojang.setCurrentText("")
        self._dojang.lineEdit().setPlaceholderText("단체명(도장) — 목록에서 고르거나 새로 입력")
        self._individual = {label: QLineEdit() for label in entry_lines(categories.individual)}
        self._free = [(QLineEdit(), QLineEdit()) for _ in range(FREE_ROWS)]
        self._teams = WrittenTeamRows(categories.team)
        page = QWidget()
        page.setObjectName("page")
        column = QVBoxLayout(page)
        column.setSpacing(SPACING)
        column.addWidget(self._dojang)
        column.addWidget(self._individual_box())
        column.addWidget(self._team_box())
        column.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(page)
        hint = QLabel(HINT)
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("명단에 넣기")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("취소")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(hint)
        layout.addWidget(scroll, 1)
        layout.addWidget(buttons)

    def _individual_box(self) -> QGroupBox:
        box = QGroupBox("개인전")
        form = QFormLayout(box)
        for label, names in self._individual.items():
            names.setPlaceholderText(NAMES_PLACEHOLDER)
            form.addRow(label, names)
        free_title = QLabel(FREE_TITLE)
        free_title.setObjectName("hint")
        free_title.setWordWrap(True)
        form.addRow(free_title)
        for category, names in self._free:
            category.setPlaceholderText(FREE_CATEGORY_PLACEHOLDER)
            names.setPlaceholderText(NAMES_PLACEHOLDER)
            form.addRow(category, names)
        return box

    def _team_box(self) -> QGroupBox:
        box = QGroupBox("단체전")
        inner = QVBoxLayout(box)
        inner.addWidget(self._teams)
        return box

    def written_form(self) -> WrittenForm:
        rows = [(label, names.text()) for label, names in self._individual.items()]
        rows += [(category.text().strip(), names.text()) for category, names in self._free if names.text().strip()]
        individuals = tuple(IndividualLine(label, split_names(text)) for label, text in rows)
        return WrittenForm(self._dojang.currentText().strip(), individuals, self._teams.values())

    def accept(self) -> None:
        form = self.written_form()
        roster = self._session.add_written_form(form)
        if not form.dojang:
            QMessageBox.warning(self, "확인해 주세요", "\n".join(roster.problems))
            return
        if roster.problems:
            QMessageBox.warning(self, "넣지 못한 줄이 있습니다", "\n".join(roster.problems))
        super().accept()
