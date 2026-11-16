"""④ 대진 화면: 랜덤 추첨, 미리보기, 손으로 고치기."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QInputDialog, QListWidget, QListWidgetItem, QMessageBox, QVBoxLayout, QWidget

from kendo_tournament.application.export_brackets import pages_for
from kendo_tournament.application.tournament_session import TournamentSession
from kendo_tournament.presentation.bracket_canvas import BracketCanvas
from kendo_tournament.presentation.widgets import button, button_row, page_layout, report_error, show_warnings, warning_label

HINT = (
    "「모두 추첨」을 누르면 부문마다 랜덤으로 대진을 짭니다(같은 도장은 최대한 떨어뜨림). "
    "고칠 때는 이름 두 개를 차례로 누르면 자리가 바뀝니다. 이름 하나를 누르고 「기권 처리」를 누르면 그 자리는 부전승이 됩니다. "
    "Ctrl+마우스 휠로 확대합니다."
)


class BracketView(QWidget):
    go_export = Signal()

    def __init__(self, session: TournamentSession) -> None:
        super().__init__()
        self._session = session
        self._picked: int | None = None
        layout = page_layout(self, "대진", HINT)
        draw_all, redraw, title, withdraw, insert = (
            button("모두 추첨", primary=True),
            button("이 부문 다시 추첨"),
            button("제목 바꾸기"),
            button("기권 처리"),
            button("추가 선수 끼워 넣기"),
        )
        draw_all.clicked.connect(self._draw_all)
        redraw.clicked.connect(self._redraw)
        title.clicked.connect(self._edit_title)
        withdraw.clicked.connect(self._withdraw)
        insert.clicked.connect(self._insert)
        layout.addLayout(button_row(draw_all, redraw, title, withdraw, insert))
        self._warnings = warning_label()
        layout.addWidget(self._warnings)

        body = QHBoxLayout()
        self._divisions = QListWidget()
        self._divisions.currentItemChanged.connect(lambda *_: self._show_current())
        side = QVBoxLayout()
        side.addWidget(self._divisions)
        body.addLayout(side, 1)
        self._canvas = BracketCanvas()
        self._canvas.slot_clicked.connect(self._slot_clicked)
        body.addWidget(self._canvas, 4)
        layout.addLayout(body, 1)

    def refresh(self) -> None:
        current = self._label()
        self._divisions.blockSignals(True)
        self._divisions.clear()
        for division in self._session.tournament.divisions:
            done = "✓ " if self._session.bracket(division.label) else "· "
            item = QListWidgetItem(f"{done}{division.label} ({len(division.entries)})")
            item.setData(Qt.ItemDataRole.UserRole, division.label)
            self._divisions.addItem(item)
            if division.label == current:
                self._divisions.setCurrentItem(item)
        if self._divisions.currentItem() is None and self._divisions.count():
            self._divisions.setCurrentRow(0)
        self._divisions.blockSignals(False)
        self._show_current()

    def _label(self) -> str | None:
        item = self._divisions.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _show_current(self, fit: bool = True) -> None:
        label = self._label()
        bracket = self._session.bracket(label) if label else None
        if bracket is None:
            self._canvas.show_pages([], set(), set())
            show_warnings(self._warnings, ["아직 추첨하지 않은 부문입니다. 「모두 추첨」을 눌러 주세요."] if label else [])
            return
        conflicts = self._session.conflicts(label)
        added, removed = self._session.pending(label)
        lines = [
            f"같은 도장끼리 첫 경기: {bracket.slots[i].name} · {bracket.slots[j].name} (피할 수 없는 경우만 남깁니다)"
            for i, j in conflicts
        ]
        lines += [f"명단에 새로 생긴 선수: {e.name}({e.dojang}) — 「추가 선수 끼워 넣기」" for e in added]
        lines += [f"명단에서 빠진 선수: {e.name}({e.dojang}) — 이름을 누르고 「기권 처리」" for e in removed]
        show_warnings(self._warnings, lines)
        picked = {self._picked} if self._picked is not None else set()
        flagged = {slot for pair in conflicts for slot in pair}
        self._canvas.show_pages(pages_for([bracket]), picked, flagged)
        if fit:
            self._canvas.fit()

    def _draw_all(self) -> None:
        if not self._session.tournament.divisions:
            show_warnings(self._warnings, ["먼저 「부문」에서 부문을 나눠 주세요."])
            return
        already = [d for d in self._session.tournament.divisions if self._session.bracket(d.label)]
        if already:
            answer = QMessageBox.question(
                self,
                "모두 추첨",
                f"이미 짠 대진 {len(already)}개도 새로 추첨할까요?\n"
                "(아니요: 아직 안 짠 부문만 추첨합니다. 손으로 고친 내용은 지켜집니다.)",
            )
            if answer == QMessageBox.StandardButton.Yes:
                for division in already:
                    self._session.draw(division.label)
        self._session.draw_missing()
        self._picked = None
        self.refresh()
        self._ask_next_step()

    def _ask_next_step(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("추첨 완료")
        box.setText("대진을 모두 짰습니다. 여기서 더 고치시겠어요, 인쇄될 모양을 확인하시겠어요?")
        edit = box.addButton("여기서 더 고치기", QMessageBox.ButtonRole.RejectRole)
        box.addButton("인쇄 모양 확인", QMessageBox.ButtonRole.AcceptRole)
        box.exec()
        if box.clickedButton() is not edit:
            self.go_export.emit()

    def _redraw(self) -> None:
        label = self._label()
        if label is None:
            return
        if self._session.bracket(label):
            answer = QMessageBox.question(self, "다시 추첨", "이 부문을 새로 추첨하면 손으로 고친 내용이 사라집니다. 계속할까요?")
            if answer != QMessageBox.StandardButton.Yes:
                return
        self._session.draw(label)
        self._picked = None
        self.refresh()

    def _slot_clicked(self, slot: int) -> None:
        label = self._label()
        if label is None:
            return
        if self._picked is None:
            self._picked = slot
        elif self._picked == slot:
            self._picked = None
        else:
            self._session.swap(label, self._picked, slot)
            self._picked = None
        self._show_current(fit=False)

    def _withdraw(self) -> None:
        label = self._label()
        if label is None or self._picked is None:
            show_warnings(self._warnings, ["기권할 선수 이름을 먼저 눌러 주세요."])
            return
        name = self._session.bracket(label).slots[self._picked].name
        if (
            QMessageBox.question(self, "기권 처리", f"{name} 선수를 대진에서 뺄까요? 그 자리는 부전승이 됩니다.")
            == QMessageBox.StandardButton.Yes
        ):
            self._session.withdraw(label, self._picked)
            self._picked = None
            self._show_current(fit=False)

    def _insert(self) -> None:
        label = self._label()
        if label is None:
            return
        added, _ = self._session.pending(label)
        if not added:
            show_warnings(
                self._warnings, ["끼워 넣을 선수가 없습니다. 명단에 선수를 추가하고 부문을 다시 나누면 여기 나타납니다."]
            )
            return
        names = [f"{e.name} ({e.dojang})" for e in added]
        chosen, ok = QInputDialog.getItem(self, "끼워 넣기", "선수", names, 0, False)
        if not ok:
            return
        try:
            self._session.insert(label, added[names.index(chosen)])
        except ValueError as error:
            report_error(self, error)
        self._show_current(fit=False)

    def _edit_title(self) -> None:
        label = self._label()
        bracket = self._session.bracket(label) if label else None
        if bracket is None:
            return
        title, ok = QInputDialog.getText(self, "제목 바꾸기", "대진표 맨 위 제목 (예: 남자 단부 개인전 B조)", text=bracket.title)
        if ok and title.strip():
            self._session.set_title(label, title.strip())
            self._show_current(fit=False)
