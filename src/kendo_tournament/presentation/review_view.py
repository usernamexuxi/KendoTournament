"""⑤ 인쇄 순서 화면: 찍힐 부문·순서·쪽 나눔을 고르고 A4 미리보기로 확인한다."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QHBoxLayout, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from kendo_tournament.application.tournament_session import TournamentSession
from kendo_tournament.presentation.print_preview import PrintPreview
from kendo_tournament.presentation.widgets import button, button_row, page_layout, show_warnings, warning_label

PAGE_BREAK_MARK = "  ⤓ 여기부터 새 종이"
NOT_DRAWN_MARK = "  (아직 대진 안 짬)"
NOT_PRINTED = "  -  "


class ReviewView(QWidget):
    def __init__(self, session: TournamentSession) -> None:
        super().__init__()
        self._session = session
        layout = page_layout(
            self,
            "인쇄 순서",
            "인쇄할 종별에 체크가 되어 있는지, 오른쪽 미리보기에서 모양을 확인하세요. 순서는 종별을 끌어 옮겨도 바뀝니다.",
        )
        check_all, check_none = button("모두 인쇄"), button("모두 빼기")
        check_all.clicked.connect(lambda: self._check(True))
        check_none.clicked.connect(lambda: self._check(False))
        self._list = QListWidget()
        self._list.setObjectName("printList")
        self._list.itemChanged.connect(self._check_changed)
        self._list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._list.model().rowsMoved.connect(self._order_dragged)
        up, down, page_break = button("▲ 위로"), button("▼ 아래로"), button("여기부터 새 종이에")
        up.clicked.connect(lambda: self._move(-1))
        down.clicked.connect(lambda: self._move(1))
        page_break.clicked.connect(self._toggle_page_break)
        reset = button("기본 순서로")
        reset.clicked.connect(self._reset_order)
        self._message = warning_label()
        choose = QVBoxLayout()
        choose.addLayout(button_row(check_all, check_none))
        choose.addWidget(self._list, 1)
        choose.addLayout(button_row(up, down, page_break, reset))
        choose.addWidget(self._message)
        self._preview = PrintPreview()
        body = QHBoxLayout()
        body.setSpacing(16)
        body.addLayout(choose, 2)
        body.addWidget(self._preview, 3)
        layout.addLayout(body, 1)

    def refresh(self, selected: str | None = None) -> None:
        self._list.blockSignals(True)
        self._list.clear()
        for label in self._session.print_order():
            self._list.addItem(self._item(label))
            if label == selected:
                self._list.setCurrentRow(self._list.count() - 1)
        self._list.blockSignals(False)
        self._update_preview()

    def _item(self, label: str) -> QListWidgetItem:
        ready = self._session.bracket(label) is not None
        item = QListWidgetItem(label if ready else label + NOT_DRAWN_MARK)
        item.setData(Qt.ItemDataRole.UserRole, label)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        checked = ready and label not in self._session.excluded_labels
        item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        if not ready:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
        return item

    def _check(self, on: bool) -> None:
        self._session.excluded_labels = set() if on else set(self._session.print_order())
        self.refresh(self._current_label())

    def _check_changed(self, item: QListWidgetItem) -> None:
        label = item.data(Qt.ItemDataRole.UserRole)
        if item.checkState() == Qt.CheckState.Checked:
            self._session.excluded_labels.discard(label)
        else:
            self._session.excluded_labels.add(label)
        self._update_preview()

    def _current_label(self) -> str | None:
        item = self._list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _move(self, step: int) -> None:
        label = self._current_label()
        if label is None:
            show_warnings(self._message, ["옮길 종별을 목록에서 먼저 눌러 주세요."])
            return
        self._session.move_in_print(label, step)
        self.refresh(label)

    def _order_dragged(self) -> None:
        label = self._current_label()
        labels = [self._list.item(row).data(Qt.ItemDataRole.UserRole) for row in range(self._list.count())]
        self._session.set_print_order(labels)
        self.refresh(label)

    def _reset_order(self) -> None:
        self._session.reset_print_order()
        self.refresh(self._current_label())

    def _toggle_page_break(self) -> None:
        label = self._current_label()
        if label is None:
            show_warnings(self._message, ["새 종이로 넘길 종별을 목록에서 먼저 눌러 주세요."])
            return
        self._session.toggle_page_break(label)
        self.refresh(label)

    def _checked_labels(self) -> list[str]:
        return [
            self._list.item(r).data(Qt.ItemDataRole.UserRole)
            for r in range(self._list.count())
            if self._list.item(r).checkState() == Qt.CheckState.Checked
        ]

    def _show_pages_in_list(self, labels: list[str]) -> None:
        """목록 글자 앞에 실리는 쪽(「2쪽」)을, 뒤에 운영자가 정한 새 쪽 표시를 붙인다."""
        numbers = self._session.page_numbers(labels)
        breaks = self._session.tournament.page_breaks
        self._list.blockSignals(True)
        for row in range(self._list.count()):
            item = self._list.item(row)
            label = item.data(Qt.ItemDataRole.UserRole)
            if self._session.bracket(label) is None:
                continue
            page = f"{numbers[label]}쪽 · " if label in numbers else NOT_PRINTED
            item.setText(page + label + (PAGE_BREAK_MARK if label in breaks else ""))
        self._list.blockSignals(False)

    def _update_preview(self) -> None:
        labels = self._checked_labels()
        self._show_pages_in_list(labels)
        self._preview.show_pages(self._session.print_pages(labels))
