"""출력 미리보기: 저장될 A4 쪽들을 인쇄 전처럼 한 쪽씩 넘겨 보거나 이어서 내려 본다."""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QDialog, QGroupBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from kendo_tournament.domain.layout.bracket_layout import PageLayout
from kendo_tournament.presentation.bracket_canvas import BracketCanvas
from kendo_tournament.presentation.widgets import button

EMPTY_PREVIEW = "왼쪽에서 부문을 체크하면 인쇄될 모양이 여기 나옵니다."


class PrintPreview(QGroupBox):
    """enlarge 면 「크게 보기」 단추로 같은 쪽들을 큰 창에 띄운다(큰 창 안의 미리보기에는 그 단추가 없다)."""

    def __init__(self, enlarge: bool = True) -> None:
        super().__init__("인쇄 미리보기 (A4)")
        self._pages: list[PageLayout] = []
        self._canvas = BracketCanvas(selectable=False)
        self._canvas.verticalScrollBar().valueChanged.connect(self._show_position)
        self._position = QLabel()
        self._position.setObjectName("hint")
        self._empty = QLabel(EMPTY_PREVIEW)
        self._empty.setObjectName("hint")
        self._empty.setWordWrap(True)
        previous, following = button("◀ 앞 쪽"), button("다음 쪽 ▶")
        whole, width = button("한 쪽 보기"), button("폭 맞춤")
        previous.clicked.connect(lambda: self._move(-1))
        following.clicked.connect(lambda: self._move(1))
        whole.clicked.connect(lambda: self._canvas.fit_page(self._canvas.visible_page()))
        width.clicked.connect(lambda: self._canvas.fit_width(self._canvas.visible_page()))
        # 단추를 한 줄에 다 놓으면 미리보기 칸이 좁을 때 단추 글자가 잘린다. 넘기기와 보기 방식을 두 줄로 나눈다.
        paging = QHBoxLayout()
        for widget in (previous, following, self._position):
            paging.addWidget(widget)
        paging.addStretch(1)
        viewing = QHBoxLayout()
        viewing.addWidget(whole)
        viewing.addWidget(width)
        if enlarge:
            big = button("크게 보기")
            big.clicked.connect(self._open_large)
            viewing.addWidget(big)
        viewing.addStretch(1)
        layout = QVBoxLayout(self)
        layout.addLayout(paging)
        layout.addLayout(viewing)
        layout.addWidget(self._empty)
        layout.addWidget(self._canvas, 1)

    def show_pages(self, pages: list[PageLayout]) -> None:
        self._pages = list(pages)
        self._canvas.show_pages(pages, set(), set())
        self._empty.setVisible(not pages)
        self._canvas.setVisible(bool(pages))
        # 화면 배치가 끝나야 창 크기를 알 수 있어 맞추기는 한 박자 뒤에 한다.
        QTimer.singleShot(0, lambda: self._canvas.fit_page(0))
        self._show_position()

    def _move(self, step: int) -> None:
        self._canvas.fit_page(self._canvas.visible_page() + step)

    def _show_position(self) -> None:
        total = self._canvas.page_count
        self._position.setText(f"{self._canvas.visible_page() + 1} / {total}쪽" if total else "")

    def _open_large(self) -> None:
        if self._pages:
            LargePreview(self._pages, self).showMaximized()


class LargePreview(QDialog):
    """미리보기를 화면 가득 띄운 창. 쪽 넘기기·한 쪽 보기·폭 맞춤은 작은 미리보기와 같다."""

    def __init__(self, pages: list[PageLayout], parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("인쇄 미리보기 — 크게 보기")
        preview = PrintPreview(enlarge=False)
        layout = QVBoxLayout(self)
        layout.addWidget(preview)
        preview.show_pages(pages)
