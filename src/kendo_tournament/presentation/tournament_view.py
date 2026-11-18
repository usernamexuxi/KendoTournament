"""① 대회 정보 화면."""

from __future__ import annotations

from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFormLayout,
    QGroupBox,
    QInputDialog,
    QLabel,
    QLineEdit,
    QWidget,
)

from kendo_tournament.application.tournament_session import TOURNAMENT_EXTENSION, TournamentSession
from kendo_tournament.domain.ports import TournamentFileError
from kendo_tournament.domain.tournament import Scope
from kendo_tournament.presentation.file_dialogs import open_file, save_file
from kendo_tournament.presentation.widgets import button, button_row, page_layout, report_error

FILE_FILTER = f"대회 파일 (*{TOURNAMENT_EXTENSION})"


class TournamentView(QWidget):
    tournament_replaced = Signal()

    def __init__(self, session: TournamentSession) -> None:
        super().__init__()
        self._session = session
        layout = page_layout(self, "대회 정보", "대회 이름과 날짜를 적으세요. 적은 내용은 저절로 저장됩니다.")

        new_button, open_button, save_as_button = button("새 대회"), button("대회 파일 열기"), button("다른 이름으로 저장")
        new_button.clicked.connect(self._new)
        open_button.clicked.connect(self._open)
        save_as_button.clicked.connect(self._save_as)
        layout.addLayout(button_row(new_button, open_button, save_as_button))

        group = QGroupBox("대회 정보")
        form = QFormLayout(group)
        self._name = QLineEdit()
        self._date = QDateEdit(calendarPopup=True)
        self._date.setDisplayFormat("yyyy-MM-dd")
        self._scope = QComboBox()
        for scope in Scope:
            self._scope.addItem(scope.value, scope.name)
        self._path = QLabel()
        self._path.setObjectName("hint")
        form.addRow("대회 이름", self._name)
        form.addRow("대회 날짜", self._date)
        form.addRow("범위", self._scope)
        form.addRow("저장 위치", self._path)
        layout.addWidget(group)
        layout.addStretch(1)

        self._name.editingFinished.connect(self._save_settings)
        self._date.dateChanged.connect(self._save_settings)
        self._scope.currentIndexChanged.connect(self._save_settings)
        self.refresh()

    def refresh(self) -> None:
        t = self._session.tournament
        widgets = (self._name, self._date, self._scope)
        for widget in widgets:
            widget.blockSignals(True)
        self._name.setText(t.name)
        held = t.held_on
        self._date.setDate(QDate(held.year, held.month, held.day) if held else QDate.currentDate())
        self._scope.setCurrentIndex(self._scope.findData(t.scope.name))
        for widget in widgets:
            widget.blockSignals(False)
        self._path.setText(str(self._session.path or self._session.default_path()))

    def _save_settings(self) -> None:
        self._session.update_settings(
            name=self._name.text().strip() or "새 대회",
            held_on=self._date.date().toPython(),
            scope=Scope[self._scope.currentData()],
        )
        self.refresh()

    def _new(self) -> None:
        name, ok = QInputDialog.getText(self, "새 대회", "대회 이름")
        if ok:
            self._session.new(name)
            self.tournament_replaced.emit()

    def _open(self) -> None:
        path = open_file(self, "대회 파일 열기", str(self._session.default_path().parent), FILE_FILTER)
        if path is None:
            return
        try:
            self._session.open(path)
        except (TournamentFileError, OSError) as error:
            report_error(self, error)
            return
        self.tournament_replaced.emit()

    def _save_as(self) -> None:
        path = save_file(self, "다른 이름으로 저장", str(self._session.default_path()), FILE_FILTER, TOURNAMENT_EXTENSION)
        if path is not None:
            self._session.save_as(path)
            self.refresh()
