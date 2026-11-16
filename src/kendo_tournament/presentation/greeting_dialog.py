"""「대회사 고치기」 창. 대회사는 대회식순·임원·일정과 따로 고친다(운영자 지시: 「대회사하고 나머지 구분」).

틀(사진 자리 · 본문 · 오른쪽 아래 날짜·직함·이름)은 그대로, 내용만 바꾼다. 칸은 greeting_editor 의 GreetingForm 이다.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QDialogButtonBox, QScrollArea, QVBoxLayout, QWidget

from kendo_tournament.domain.greeting import Greeting
from kendo_tournament.domain.ports import ExportError
from kendo_tournament.presentation.greeting_editor import GreetingForm
from kendo_tournament.presentation.screen_fit_dialog import ScreenFitDialog
from kendo_tournament.presentation.widgets import report_error

SCREEN_SHARE = 0.85
MAX_WIDTH, MAX_HEIGHT = 900, 860

GreetingSave = Callable[[Greeting], None]


class GreetingDialog(ScreenFitDialog):
    """「저장」을 누르면 고친 대회사를 save 로 넘긴다. ExportError(사진을 못 읽음)면 알리고 창을 닫지 않는다."""

    def __init__(self, greeting: Greeting, save: GreetingSave, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("대회사 고치기")
        self._save = save
        screen = self.screen().availableGeometry()
        self.resize(min(MAX_WIDTH, int(screen.width() * SCREEN_SHARE)), min(MAX_HEIGHT, int(screen.height() * SCREEN_SHARE)))
        self._form = GreetingForm(greeting)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(self._form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("저장")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("취소")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(scroll, 1)
        layout.addWidget(buttons)

    def accept(self) -> None:
        try:
            self._save(self._form.result_greeting())
        except ExportError as error:
            report_error(self, error)
            return
        super().accept()
