"""「대회사 고치기」 창(greeting_dialog)의 칸. 틀(사진 자리 · 본문 · 오른쪽 아래 날짜·직함·이름)은 그대로, 내용만 바꾼다."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from kendo_tournament.domain.greeting import Greeting
from kendo_tournament.presentation.file_dialogs import open_file
from kendo_tournament.presentation.widgets import button

PHOTO_FILTER = "사진 (*.png *.jpg *.jpeg)"
THUMB_WIDTH, THUMB_HEIGHT = 120, 148
BODY_MIN_HEIGHT = 220
NO_PHOTO = "사진 없음"
BODY_HINT = "빈 줄로 문단을 나눕니다. 첫 문단은 사진 오른쪽에, 나머지는 사진 아래에 들어갑니다."
DATE_PLACEHOLDER = "비우면 대회 날짜 (예: 2026. 4. 12)"


class GreetingForm(QWidget):
    """result_greeting() 으로 고친 내용을 돌려준다. 사진은 경로만 바꾸고 읽기는 책자가 한다."""

    def __init__(self, greeting: Greeting) -> None:
        super().__init__()
        self.setObjectName("page")
        self._greeting = greeting
        self._photo_file = greeting.photo_file
        self._thumb = QLabel()
        self._thumb.setObjectName("logoSlot")
        self._thumb.setFixedSize(THUMB_WIDTH, THUMB_HEIGHT)
        self._thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._body = QPlainTextEdit(greeting.body)
        self._body.setMinimumHeight(BODY_MIN_HEIGHT)
        self._date = QLineEdit(greeting.date_text)
        self._date.setPlaceholderText(DATE_PLACEHOLDER)
        self._position = QLineEdit(greeting.position)
        self._name = QLineEdit(greeting.name)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(self._photo_card())
        layout.addWidget(self._body_card(), 1)
        layout.addWidget(self._signature_card())
        self._show_photo()

    def _photo_card(self) -> QFrame:
        choose, clear = button("사진 고르기", primary=True), button("사진 빼기")
        choose.clicked.connect(self._choose_photo)
        clear.clicked.connect(self._clear_photo)
        side = QVBoxLayout()
        side.addWidget(_title("사진 칸"))
        side.addWidget(_hint("PNG·JPG. 왼쪽 위 사진 칸에 비율을 지켜 들어갑니다."))
        row = QHBoxLayout()
        row.addWidget(choose)
        row.addWidget(clear)
        row.addStretch(1)
        side.addLayout(row)
        side.addStretch(1)
        card = _card()
        line = QHBoxLayout(card)
        line.addWidget(self._thumb)
        line.addLayout(side, 1)
        return card

    def _body_card(self) -> QFrame:
        card = _card()
        column = QVBoxLayout(card)
        column.addWidget(_title("내용 칸"))
        column.addWidget(_hint(BODY_HINT))
        column.addWidget(self._body, 1)
        return card

    def _signature_card(self) -> QFrame:
        card = _card()
        column = QVBoxLayout(card)
        column.addWidget(_title("오른쪽 아래 칸"))
        form = QFormLayout()
        form.addRow("날짜", self._date)
        form.addRow("직함", self._position)
        form.addRow("이름", self._name)
        column.addLayout(form)
        return card

    def _choose_photo(self) -> None:
        path = open_file(self, "대회사 사진 고르기", "", PHOTO_FILTER)
        if path is not None:
            self._photo_file = str(path)
            self._show_photo()

    def _clear_photo(self) -> None:
        self._photo_file = ""
        self._show_photo()

    def _show_photo(self) -> None:
        pixmap = QPixmap(self._photo_file) if self._photo_file else QPixmap()
        if pixmap.isNull():
            self._thumb.setPixmap(QPixmap())
            self._thumb.setText(Path(self._photo_file).name if self._photo_file else NO_PHOTO)
            return
        mode = Qt.AspectRatioMode.KeepAspectRatio
        self._thumb.setPixmap(pixmap.scaled(THUMB_WIDTH, THUMB_HEIGHT, mode, Qt.TransformationMode.SmoothTransformation))

    def result_greeting(self) -> Greeting:
        return replace(
            self._greeting,
            body=self._body.toPlainText().strip(),
            date_text=self._date.text().strip(),
            position=self._position.text().strip(),
            name=self._name.text().strip(),
            photo_file=self._photo_file,
        )


def _card() -> QFrame:
    card = QFrame()
    card.setObjectName("card")
    return card


def _title(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("cardTitle")
    return label


def _hint(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("hint")
    label.setWordWrap(True)
    return label
