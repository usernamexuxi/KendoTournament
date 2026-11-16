"""② 명단 화면: 문서 불러오기, 명단 확인·수정, 같은 도장 묶기."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from kendo_tournament.application.tournament_session import TournamentSession
from kendo_tournament.domain.division.grade import parse_grade, resolve_grade
from kendo_tournament.domain.model import Participant
from kendo_tournament.domain.roster_check import duplicate_check_requests, missing_fields, missing_gender_requests
from kendo_tournament.domain.text_values import parse_age, parse_gender
from kendo_tournament.presentation.file_dialogs import open_files
from kendo_tournament.presentation.participant_dialog import ParticipantDialog
from kendo_tournament.presentation.style import WARN_SOFT
from kendo_tournament.presentation.widgets import TABLE_ROW_HEIGHT, button, button_row, page_layout, show_warnings, warning_label
from kendo_tournament.presentation.written_form_dialog import WrittenFormDialog

# 나이는 세는나이다. 세는나이는 학년과 하나씩 맞물리지만(8세=초1) 만 나이는 생일에 따라 한 학년에 두 나이가 섞인다.
COLUMNS = ("도장", "이름", "성별", "학년", "나이(세는나이)", "구분", "종목", "가져온 파일")
INDIVIDUAL_LABEL = "개인전"
TEAM_LABEL = "단체전"
# 불러오기 알림·성별 요청·서류 확인(중복 의심)을 한 칸에 모아 보여 준다. 성별 요청이 많아도 다른 알림이 밀려나지 않게 넉넉히.
WARNING_LIMIT = 16
EDITABLE = {0: "dojang", 1: "name", 2: "gender", 3: "grade", 4: "age"}


def needs_check(person: Participant, team_member: bool = False) -> bool:
    """team_member 면 단체전 팀원이다. 팀원의 빈 성별은 혼성 팀이라 확인할 일이 아니다."""
    return bool(missing_fields(person, mixed_team_member=team_member))


class RosterView(QWidget):
    roster_changed = Signal()

    def __init__(self, session: TournamentSession, accepted_extensions: tuple[str, ...]) -> None:
        super().__init__()
        self._session = session
        self._accepted = accepted_extensions
        self._import_messages: list[str] = []
        self.setAcceptDrops(True)
        layout = page_layout(
            self,
            "명단",
            "신청 문서(한글·워드·PDF)를 불러오거나 이 창에 끌어다 놓으세요. "
            "주황색 줄은 확인이 필요한 선수입니다. 칸을 두 번 눌러 고칠 수 있습니다. 나이는 세는나이(한국 나이)로 적습니다.",
        )
        load, written, add, remove, merge = (
            button("신청 문서 불러오기", primary=True),
            button("신청서 직접 작성"),
            button("선수 추가"),
            button("선택 삭제"),
            button("같은 도장으로 묶기"),
        )
        load.clicked.connect(self._choose_files)
        written.clicked.connect(self._write_form)
        add.clicked.connect(self._add_person)
        remove.clicked.connect(self._remove_selected)
        merge.clicked.connect(self._merge_dojangs)
        layout.addLayout(button_row(load, written, add, remove))
        self._warnings = warning_label()
        layout.addWidget(self._warnings)

        body = QHBoxLayout()
        self._table = QTableWidget(0, len(COLUMNS))
        self._table.setHorizontalHeaderLabels(COLUMNS)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setDefaultSectionSize(TABLE_ROW_HEIGHT)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.itemChanged.connect(self._cell_edited)
        body.addWidget(self._table, 3)
        side = QVBoxLayout()
        self._dojangs = QListWidget()
        self._dojangs.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        side.addWidget(self._dojangs, 1)
        side.addWidget(merge)
        body.addLayout(side, 1)
        layout.addLayout(body, 1)
        self.refresh()

    def refresh(self) -> None:
        people = self._session.tournament.participants
        team_of = {member: team.name for team in self._session.tournament.teams for member in team.member_ids}
        self._table.blockSignals(True)
        self._table.setRowCount(len(people))
        for row, person in enumerate(people):
            grade = resolve_grade(person)
            values = (
                person.dojang,
                person.name,
                person.gender.value if person.gender else "",
                person.grade.label if person.grade else "",
                "" if person.age is None else str(person.age),
                grade.label if grade else "확인 필요",
                f"{TEAM_LABEL} ({team_of[person.id]})" if person.id in team_of else INDIVIDUAL_LABEL,
                person.source,
            )
            flagged = needs_check(person, team_member=person.id in team_of)
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, person.id)
                if column not in EDITABLE:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if flagged:
                    item.setBackground(QColor(WARN_SOFT))
                self._table.setItem(row, column, item)
        self._table.blockSignals(False)
        self._table.resizeColumnsToContents()
        self._refresh_dojangs()

    def _refresh_dojangs(self) -> None:
        t = self._session.tournament
        self._dojangs.clear()
        counts: dict[str, int] = {}
        for person in t.participants:
            counts[person.dojang] = counts.get(person.dojang, 0) + 1
        for name in t.dojang_names():
            item = QListWidgetItem(f"{name}  ({counts[name]}명)")
            item.setData(Qt.ItemDataRole.UserRole, name)
            self._dojangs.addItem(item)
        duplicates = duplicate_check_requests(t.duplicate_people())
        # 불러오기 알림을 여기서 함께 다시 보여 준다. 전에는 불러온 직후 이 갱신이 알림 칸을 덮어써 알림이 사라졌다.
        lines = self._import_messages + missing_gender_requests(t.participants, t.teams) + duplicates
        show_warnings(self._warnings, lines, limit=WARNING_LIMIT)

    def import_paths(self, paths: list[Path]) -> None:
        report = self._session.import_files(paths)
        self._import_messages = list(report.rejected) + list(report.problems)
        self.refresh()
        self.roster_changed.emit()

    def _choose_files(self) -> None:
        patterns = " ".join(f"*{ext}" for ext in self._accepted)
        files = open_files(self, "신청 문서 불러오기", "", f"신청 문서 ({patterns})")
        if files:
            self.import_paths(files)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        self.import_paths([Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()])

    def _cell_edited(self, item: QTableWidgetItem) -> None:
        field = EDITABLE.get(item.column())
        if field is None:
            return
        text = item.text().strip()
        converters = {"gender": parse_gender, "grade": lambda v: parse_grade(v) if v else None, "age": parse_age}
        value = converters[field](text) if field in converters else text
        self._session.rename_participant(item.data(Qt.ItemDataRole.UserRole), **{field: value})
        self.refresh()
        self.roster_changed.emit()

    def _write_form(self) -> None:
        if WrittenFormDialog(self._session, self).exec() == WrittenFormDialog.DialogCode.Accepted:
            self.refresh()
            self.roster_changed.emit()

    def _add_person(self) -> None:
        dialog = ParticipantDialog(self._session.tournament.dojang_names(), self)
        if dialog.exec() and dialog.participant is not None:
            self._session.set_participants(self._session.tournament.participants + [dialog.participant])
            self.refresh()
            self.roster_changed.emit()

    def _remove_selected(self) -> None:
        rows = {index.row() for index in self._table.selectedIndexes()}
        ids = {self._table.item(row, 0).data(Qt.ItemDataRole.UserRole) for row in rows}
        if ids:
            self._session.set_participants([p for p in self._session.tournament.participants if p.id not in ids])
            self.refresh()
            self.roster_changed.emit()

    def _merge_dojangs(self) -> None:
        names = [item.data(Qt.ItemDataRole.UserRole) for item in self._dojangs.selectedItems()]
        if len(names) < 2:
            show_warnings(self._warnings, ["오른쪽 도장 목록에서 같은 도장인 이름을 두 개 이상 골라 주세요 (Ctrl+클릭)."])
            return
        chosen, ok = QInputDialog.getItem(self, "같은 도장으로 묶기", "대표 이름", names, 0, False)
        if ok:
            self._session.merge_dojangs(names, chosen)
            show_warnings(self._warnings, [f"{', '.join(names)} 를 같은 도장으로 보고 대진을 짭니다."])
            self.roster_changed.emit()
