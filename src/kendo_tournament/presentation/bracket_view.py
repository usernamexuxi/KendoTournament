"""④ 대진 짜기 화면: 랜덤 추첨, 미리보기, 손으로 고치기."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QInputDialog, QLabel, QListWidget, QListWidgetItem, QMessageBox, QVBoxLayout, QWidget

from kendo_tournament.application.export_brackets import pages_for
from kendo_tournament.application.tournament_session import TournamentSession
from kendo_tournament.domain.draw.bracket import Bracket
from kendo_tournament.domain.model import Event
from kendo_tournament.presentation.bracket_canvas import BracketCanvas
from kendo_tournament.presentation.widgets import (
    button,
    button_row,
    empty_state,
    page_layout,
    report_error,
    show_warnings,
    warning_label,
)

DRAW_ALL = "대진 자동으로 짜기"
HINT = f"「{DRAW_ALL}」를 누르세요. 자리를 바꾸려면 대진표에서 이름 두 개를 차례로 누르세요."
PICK_HINT = "「{name}」 선수를 골랐습니다. 자리를 바꿀 다른 선수 이름을 누르세요. 빼려면 「선수 빼기(기권)」. 다시 누르면 취소."
NO_DIVISIONS = "아직 나눈 종별이 없습니다.\n「③ 종별 나누기」에서 선수를 종별로 나눠 주세요."
NOT_DRAWN = f"이 종별은 아직 대진을 짜지 않았습니다.\n위 「{DRAW_ALL}」를 누르세요."
LIST_MIN_WIDTH = 340
ZOOM_STEP = 1.25


class BracketView(QWidget):
    go_export = Signal()

    def __init__(self, session: TournamentSession) -> None:
        super().__init__()
        self._session = session
        self._picked: int | None = None
        layout = page_layout(self, "대진 짜기", HINT)
        draw_all, redraw, title, withdraw, insert = (
            button(DRAW_ALL, primary=True),
            button("이 종별만 다시 짜기"),
            button("대진표 제목 바꾸기"),
            button("선수 빼기(기권)"),
            button("새 선수 넣기"),
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
        self._divisions.setMinimumWidth(LIST_MIN_WIDTH)
        self._divisions.setWordWrap(True)
        self._divisions.currentItemChanged.connect(lambda *_: self._show_current())
        body.addWidget(self._divisions, 2)
        self._canvas = BracketCanvas()
        self._canvas.slot_clicked.connect(self._slot_clicked)
        bigger, smaller, whole = button("＋ 크게"), button("－ 작게"), button("전체 보기")
        bigger.clicked.connect(lambda: self._canvas.zoom(ZOOM_STEP))
        smaller.clicked.connect(lambda: self._canvas.zoom(1 / ZOOM_STEP))
        whole.clicked.connect(self._canvas.fit_drawing)
        self._pick_hint = QLabel()
        self._pick_hint.setObjectName("pickHint")
        self._pick_hint.setWordWrap(True)
        self._pick_hint.hide()
        self._board_title = QLabel()
        self._board_title.setObjectName("boardTitle")
        self._board_info = QLabel()
        self._board_info.setObjectName("boardInfo")
        heading = QVBoxLayout()
        heading.setSpacing(2)
        heading.addWidget(self._board_title)
        heading.addWidget(self._board_info)
        top = QHBoxLayout()
        top.addLayout(heading, 1)
        top.addLayout(button_row(bigger, smaller, whole))
        # 대진이 없으면 확대 단추·빈 캔버스 대신 큰 안내 하나만 둔다(빈 회색 칸과 스크롤 막대만 남던 화면).
        self._board = QWidget()
        board = QVBoxLayout(self._board)
        board.setContentsMargins(0, 0, 0, 0)
        board.addLayout(top)
        board.addWidget(self._pick_hint)
        board.addWidget(self._canvas, 1)
        self._empty = empty_state(NO_DIVISIONS)
        view = QVBoxLayout()
        view.addWidget(self._board, 1)
        view.addWidget(self._empty, 1)
        body.addLayout(view, 5)
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
        self._divisions.setVisible(self._divisions.count() > 0)
        self._divisions.blockSignals(False)
        self._show_current()

    def _label(self) -> str | None:
        item = self._divisions.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _show_current(self, fit: bool = True) -> None:
        label = self._label()
        bracket = self._session.bracket(label) if label else None
        self._board.setVisible(bracket is not None)
        self._empty.setVisible(bracket is None)
        if bracket is None:
            self._canvas.show_pages([], set(), set())
            self._empty.setText(NOT_DRAWN if label else NO_DIVISIONS)
            show_warnings(self._warnings, [])
            return
        division = self._session.division(label)
        self._board_title.setText(division.label)
        unit = "팀" if division.event is Event.TEAM else "명"
        self._board_info.setText(f"{division.event.value} · {len(division.entries)}{unit}")
        conflicts = self._session.conflicts(label)
        added, removed = self._session.pending(label)
        lines = [
            f"같은 도장끼리 첫 경기: {bracket.slots[i].name} · {bracket.slots[j].name} (피할 수 없는 경우만 남깁니다)"
            for i, j in conflicts
        ]
        lines += [f"명단에 새로 생긴 선수: {e.name}({e.dojang}) — 「새 선수 넣기」" for e in added]
        lines += [f"명단에서 빠진 선수: {e.name}({e.dojang}) — 이름을 누르고 「선수 빼기(기권)」" for e in removed]
        show_warnings(self._warnings, lines)
        self._show_pick_hint(bracket)
        picked = {self._picked} if self._picked is not None else set()
        flagged = {slot for pair in conflicts for slot in pair}
        self._canvas.show_pages(pages_for([bracket]), picked, flagged)
        if fit:
            self._canvas.fit_drawing()

    def _draw_all(self) -> None:
        if not self._session.tournament.divisions:
            show_warnings(self._warnings, ["먼저 「③ 종별 나누기」에서 선수를 종별로 나눠 주세요."])
            return
        already = [d for d in self._session.tournament.divisions if self._session.bracket(d.label)]
        if already:
            answer = QMessageBox.question(
                self,
                DRAW_ALL,
                f"이미 짠 대진 {len(already)}개도 새로 추첨할까요?\n"
                "(아니요: 아직 안 짠 종별만 짭니다. 손으로 고친 내용은 지켜집니다.)",
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
        box.setWindowTitle("대진 짜기 끝")
        box.setText("대진을 모두 짰습니다. 여기서 더 고치시겠어요, 인쇄될 모양을 확인하시겠어요?")
        edit = box.addButton("여기서 더 고치기", QMessageBox.ButtonRole.RejectRole)
        box.addButton("인쇄 순서 보러 가기", QMessageBox.ButtonRole.AcceptRole)
        box.exec()
        if box.clickedButton() is not edit:
            self.go_export.emit()

    def _redraw(self) -> None:
        label = self._label()
        if label is None:
            return
        if self._session.bracket(label):
            answer = QMessageBox.question(self, "다시 짜기", "이 종별을 새로 짜면 손으로 고친 내용이 사라집니다. 계속할까요?")
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
            show_warnings(self._warnings, ["뺄 선수 이름을 대진표에서 먼저 눌러 주세요."])
            return
        name = self._session.bracket(label).slots[self._picked].name
        if (
            QMessageBox.question(self, "선수 빼기(기권)", f"{name} 선수를 대진에서 뺄까요? 그 자리는 부전승이 됩니다.")
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
            show_warnings(self._warnings, ["넣을 새 선수가 없습니다. 명단에 선수를 추가하고 종별을 다시 나누면 여기 나타납니다."])
            return
        names = [f"{e.name} ({e.dojang})" for e in added]
        chosen, ok = QInputDialog.getItem(self, "새 선수 넣기", "선수", names, 0, False)
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
        title, ok = QInputDialog.getText(
            self, "대진표 제목 바꾸기", "대진표 맨 위 제목 (예: 남자 단부 개인전 B조)", text=bracket.title
        )
        if ok and title.strip():
            self._session.set_title(label, title.strip())
            self._show_current(fit=False)

    def _show_pick_hint(self, bracket: Bracket) -> None:
        """이름을 하나 고른 뒤 무엇을 하면 되는지 대진표 바로 위에 알린다."""
        entry = bracket.slots[self._picked] if self._picked is not None else None
        self._pick_hint.setVisible(entry is not None)
        if entry is not None:
            self._pick_hint.setText(PICK_HINT.format(name=entry.name))
