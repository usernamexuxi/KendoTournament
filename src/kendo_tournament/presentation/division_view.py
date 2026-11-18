"""③ 종별 나누기 화면: 위에서 기준을 채우고, (필요하면 펼쳐서) 고치고, 아래에서 나뉜 결과를 본다.

화면에는 「부문」 대신 신청서·요강에 늘 나오는 「종별」, 「규칙」 대신 「기준」이라고 쓴다(운영자가 쉬운 말을 원함).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHeaderView,
    QLineEdit,
    QScrollArea,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from kendo_tournament.application.tournament_session import TournamentSession
from kendo_tournament.domain.division.age_bands import band_text, rule_age
from kendo_tournament.domain.division.builder import DivisionResult
from kendo_tournament.domain.division.presets import PresetChoice, make_rules
from kendo_tournament.domain.division.unplaced import missing_rules
from kendo_tournament.domain.model import DivisionRule
from kendo_tournament.presentation.category_table_bar import CategoryTableBar
from kendo_tournament.presentation.category_table_dialog import CategoryTableDialog
from kendo_tournament.presentation.division_result import DivisionResultBox
from kendo_tournament.presentation.rule_widgets import (
    EVENT_CHOICES,
    GENDER_CHOICES,
    GRADE_CHOICES,
    MINIMUM_CHOICES,
    PresetBox,
    ValueCombo,
)
from kendo_tournament.presentation.widgets import button, button_row, page_layout, report_error

RULE_COLUMNS = ("종목", "성별", "학년부터", "학년까지", "어른 나이", "적으면 합치기", "")
EVENT, GENDER, FROM, TO, AGE, MINIMUM, DELETE = range(len(RULE_COLUMNS))
AGE_PLACEHOLDER = "예: 청년부 20-35"
RULE_ROW_HEIGHT = 54
CELL_GAP = 16
VISIBLE_RULE_ROWS = 6
NOTHING_TO_SPLIT = "고르신 종별은 더 쪼갤 수 없습니다(한 학년뿐이거나, 쪼개면 혼자인 학년이 생깁니다)."
APPLY_LABEL = "선수를 종별로 나누기"
SHOW_RULES = "▼ 나누는 기준 자세히 보기·고치기 ({count}줄)"
HIDE_RULES = "▲ 나누는 기준 접기"


class DivisionView(QWidget):
    divisions_changed = Signal()

    def __init__(self, session: TournamentSession, accepted_extensions: tuple[str, ...]) -> None:
        super().__init__()
        self._session = session
        self._accepted = accepted_extensions
        content = QWidget()
        layout = page_layout(content, "종별 나누기", f"「기준 채우기」를 누른 다음 「{APPLY_LABEL}」를 누르세요.")
        self._categories = CategoryTableBar()
        self._categories.edit_requested.connect(self._edit_categories)
        layout.addWidget(self._categories)
        presets = PresetBox()
        presets.preset_requested.connect(self._add_preset)
        layout.addWidget(presets)
        self._rules_toggle = button("")
        self._rules_toggle.clicked.connect(self._toggle_rules)
        layout.addLayout(button_row(self._rules_toggle))
        self._rules = self._rules_box()
        self._rules.hide()
        layout.addWidget(self._rules)
        apply = button(APPLY_LABEL, primary=True)
        apply.clicked.connect(self._apply)
        layout.addLayout(button_row(apply))
        self._result = DivisionResultBox()
        self._result.merge_requested.connect(lambda labels: self._edit(self._session.merge_divisions, labels))
        self._result.split_requested.connect(self._split)
        self._result.merge_groups_requested.connect(self._merge_groups)
        self._result.fix_requested.connect(self._add_missing_rules)
        layout.addWidget(self._result)
        layout.addStretch(1)
        # 표와 결과를 옆으로 놓으면 보통 노트북 폭에서 표 칸이 잘린다. 위아래로 쌓고 화면을 스크롤한다.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        self.refresh()

    def _rules_box(self) -> QGroupBox:
        box = QGroupBox("나누는 기준 — 종별마다 한 줄. 보통은 고칠 필요가 없습니다")
        inner = QVBoxLayout(box)
        self._table = QTableWidget(0, len(RULE_COLUMNS))
        self._table.setHorizontalHeaderLabels(RULE_COLUMNS)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(RULE_ROW_HEIGHT)
        self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._table.setShowGrid(False)
        self._fit_columns()
        self._table.setMinimumHeight(RULE_ROW_HEIGHT * (VISIBLE_RULE_ROWS + 1))
        inner.addWidget(self._table)
        clear = button("기준 모두 지우기")
        clear.clicked.connect(self._clear_rules)
        inner.addLayout(button_row(clear))
        return box

    def _fit_columns(self) -> None:
        """칸마다 머리글과 상자 글자가 다 보이는 폭을 준다. 고르게 나누면 좁은 창에서 글자가 잘린다.

        Qt 가 재는 상자 폭에는 스타일시트의 바깥 여백이 빠져 있어 CELL_GAP 을 더한다. 창이 좁으면 가로 스크롤.
        """
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        for column in range(self._table.columnCount()):
            widths = [header.sectionSizeHint(column)]
            for row in range(self._table.rowCount()):
                widget = self._table.cellWidget(row, column)
                widget.ensurePolished()
                widths.append(widget.sizeHint().width() + CELL_GAP)
            self._table.setColumnWidth(column, max(widths))

    def refresh(self) -> None:
        self._categories.show_table(self._session.tournament.categories)
        self._table.setRowCount(0)
        for rule in self._session.tournament.rules:
            self._append_row(rule)
        self._fit_columns()
        self._show_rule_count()
        self._show_result()

    def _toggle_rules(self) -> None:
        self._rules.setVisible(not self._rules.isVisible())
        self._show_rule_count()

    def _clear_rules(self) -> None:
        self._table.setRowCount(0)
        self._show_rule_count()

    def _show_rule_count(self) -> None:
        shown = self._rules.isVisible()
        self._rules_toggle.setText(HIDE_RULES if shown else SHOW_RULES.format(count=self._table.rowCount()))

    def _append_row(self, rule: DivisionRule) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        event = ValueCombo(EVENT_CHOICES, rule.event)
        cells = {
            EVENT: event,
            GENDER: ValueCombo(GENDER_CHOICES, rule.gender),
            FROM: ValueCombo(GRADE_CHOICES, rule.grade_from),
            TO: ValueCombo(GRADE_CHOICES, rule.grade_to),
            AGE: _age_field(rule),
            MINIMUM: ValueCombo(MINIMUM_CHOICES, rule.min_entries),
        }
        for column, widget in cells.items():
            self._table.setCellWidget(row, column, widget)
        event.setProperty("rule_id", rule.id)
        delete = button("삭제")
        delete.clicked.connect(lambda _=False, combo=event: self._delete_row_of(combo))
        self._table.setCellWidget(row, DELETE, delete)

    def _delete_row_of(self, event_combo: ValueCombo) -> None:
        for row in range(self._table.rowCount()):
            if self._table.cellWidget(row, EVENT) is event_combo:
                self._table.removeRow(row)
                self._show_rule_count()
                return

    def _rules_in_table(self) -> list[DivisionRule]:
        rules = []
        for row in range(self._table.rowCount()):
            cell = self._table.cellWidget
            event = cell(row, EVENT).value()
            age_from, age_to, age_name = rule_age(cell(row, AGE).text())
            rules.append(
                DivisionRule(
                    cell(row, EVENT).property("rule_id") or f"r{row + 1}",
                    event,
                    cell(row, GENDER).value(),
                    cell(row, FROM).value(),
                    cell(row, TO).value(),
                    None,
                    cell(row, MINIMUM).value(),
                    age_from,
                    age_to,
                    age_name,
                )
            )
        return rules

    def _edit_categories(self) -> None:
        dialog = CategoryTableDialog(self._session.tournament.categories, self._session.categories_in_file, self._accepted, self)
        if dialog.exec() != CategoryTableDialog.DialogCode.Accepted:
            return
        try:
            self._session.set_categories(dialog.result_table())
        except ValueError as error:
            report_error(self, error)
            return
        self._categories.show_table(self._session.tournament.categories)

    def _add_preset(self, choice: PresetChoice) -> None:
        existing = [self._table.cellWidget(r, EVENT).property("rule_id") for r in range(self._table.rowCount())]
        tournament = self._session.tournament
        choice = replace(choice, categories=tournament.categories)
        for rule in make_rules(choice, existing, tournament.teams, tournament.participants):
            self._append_row(rule)
        self._fit_columns()
        self._show_rule_count()

    def _apply(self) -> None:
        try:
            self._session.set_rules(self._rules_in_table())
        except ValueError as error:
            report_error(self, error)
            return
        self._show_result()
        self.divisions_changed.emit()

    def _add_missing_rules(self) -> None:
        """빠진 선수·팀이 들어갈 규칙을 표 끝에 더하고 바로 다시 나눈다."""
        result = self._session.last_division_result
        if result is None:
            return
        existing = [self._table.cellWidget(r, EVENT).property("rule_id") for r in range(self._table.rowCount())]
        for rule in missing_rules(result, existing, self._session.tournament.participants):
            self._append_row(rule)
        self._fit_columns()
        self._apply()

    def _show_result(self) -> None:
        self._result.show_divisions(self._session.tournament.divisions, self._session.last_division_result)

    def _edit(self, change: Callable[[list[str]], DivisionResult], labels: list[str]) -> bool:
        """나뉜 부문을 손으로 고치고 표·목록을 새로 그린다. 고쳤으면 True."""
        if not labels:
            self._result.notify("목록에서 종별을 먼저 골라 주세요.")
            return False
        try:
            change(labels)
        except ValueError as error:
            report_error(self, error)
            return False
        self.refresh()
        self.divisions_changed.emit()
        return True

    def _merge_groups(self, groups: list[list[str]]) -> None:
        """부전승 점검의 추천대로 합친다. 묶음마다 하나로 합치고, 묶음끼리는 따로 둔다."""
        labels = [label for group in groups for label in group]
        self._edit(lambda _: self._session.merge_division_groups(groups), labels)

    def _split(self, labels: list[str]) -> None:
        before = [d.label for d in self._session.tournament.divisions]
        changed = self._edit(self._session.split_divisions, labels)
        if changed and before == [d.label for d in self._session.tournament.divisions]:
            self._result.notify(NOTHING_TO_SPLIT)


def _age_field(rule: DivisionRule) -> QLineEdit:
    field = QLineEdit(band_text(rule.age_name, rule.age_from, rule.age_to))
    field.setPlaceholderText(AGE_PLACEHOLDER)
    return field
