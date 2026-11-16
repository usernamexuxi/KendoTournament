"""선수를 손으로 추가하는 창. 신청서 없이 현장에서 받은 선수를 넣을 때 쓴다."""

from __future__ import annotations

import uuid

from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QSpinBox, QVBoxLayout

from kendo_tournament.domain.model import ALL_GRADES, Gender, Participant
from kendo_tournament.domain.roster_check import missing_fields

MANUAL_SOURCE = "직접 입력"
NO_AGE = 0
MAX_AGE = 99


class ParticipantDialog(QDialog):
    def __init__(self, dojang_names: list[str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("선수 추가")
        self.setMinimumWidth(420)
        self._dojang = QComboBox()
        self._dojang.setEditable(True)
        self._dojang.addItems(dojang_names)
        self._dojang.setCurrentText("")
        self._dojang.lineEdit().setPlaceholderText("목록에서 고르거나 새로 입력")
        self._name = QLineEdit()
        self._gender = QComboBox()
        self._gender.addItem("고르세요", None)
        for gender in Gender:
            self._gender.addItem(f"{gender.value}자", gender.name)
        self._grade = QComboBox()
        self._grade.addItem("모름(나이로 계산)", None)
        for grade in ALL_GRADES:
            self._grade.addItem(grade.label, grade.value)
        self._age = QSpinBox()
        self._age.setRange(NO_AGE, MAX_AGE)
        self._age.setSpecialValueText("모름")
        self._error = QLabel()
        self._error.setObjectName("warning")
        self._error.setWordWrap(True)
        self._error.hide()

        form = QFormLayout()
        form.addRow("도장", self._dojang)
        form.addRow("이름", self._name)
        form.addRow("성별", self._gender)
        form.addRow("학년", self._grade)
        form.addRow("나이(세는나이)", self._age)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept_if_complete)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self._error)
        layout.addWidget(buttons)
        self.participant: Participant | None = None

    def _build(self) -> Participant:
        gender_name = self._gender.currentData()
        grade_value = self._grade.currentData()
        return Participant(
            id=f"{MANUAL_SOURCE}#{uuid.uuid4().hex[:8]}",
            name=self._name.text().strip(),
            gender=Gender[gender_name] if gender_name else None,
            dojang=self._dojang.currentText().strip(),
            grade=next((g for g in ALL_GRADES if g.value == grade_value), None),
            age=self._age.value() or None,
            source=MANUAL_SOURCE,
        )

    def _accept_if_complete(self) -> None:
        person = self._build()
        missing = missing_fields(person)
        if missing:
            self._error.setText(f"다음 항목을 채워 주세요: {', '.join(missing)}")
            self._error.show()
            return
        self.participant = person
        self.accept()
