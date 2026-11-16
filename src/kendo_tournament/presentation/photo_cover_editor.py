"""표지를 고치는 창: 앞표지 사진 · 제목 줄 · 오른쪽 아래 날짜·장소 · 맨 아래 주최·주관·후원 · 뒤표지 사진 · 광명시 로고.

글꼴과 자리는 참고 카탈로그 그대로 고정이고 여기서는 내용만 바꾼다(운영자 지시). 사진을 안 고르면 카탈로그 사진이다.
사진은 카탈로그·저장 폴더 「표지사진」의 사진을 한눈에 보며 고르거나 다른 파일에서 고른다(cover_photo_picker).
"""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from kendo_tournament.application.output_book import OutputBook
from kendo_tournament.domain.ports import ExportError
from kendo_tournament.presentation.cover_photo_picker import CoverPhotoPicker, PickerText
from kendo_tournament.presentation.file_dialogs import open_file
from kendo_tournament.presentation.screen_fit_dialog import ScreenFitDialog
from kendo_tournament.presentation.widgets import button, report_error

PHOTO_FILTER = "사진 (*.png *.jpg *.jpeg)"
FRONT_HINT = (
    "카탈로그와 「표지사진」 폴더의 사진이 보입니다. 눌러서 고르세요. 밝은 사진은 글자가 보이게 위·아래를 조금 어둡게 합니다."
)
BACK_HINT = (
    "카탈로그를 고르면 카탈로그 뒤표지(로고·문구 포함) 그대로입니다. 다른 사진을 고르면 아래쪽에 광명시 로고와 "
    "「한국관광의 별·한국대표관광지 100선 광명동굴」 로고를 얹고, 밝은 사진은 아래를 조금 어둡게 합니다."
)
LOGO_HINT = (
    "카탈로그의 광명시 로고가 들어 있습니다. 다른 로고로 바꾸려면 고르세요(PNG·JPG, 흰 바탕은 지웁니다). "
    "로고 자리가 어두우면 흰색, 밝으면 진한 색으로 얹습니다."
)
TITLE_PLACEHOLDER = "비우면 대회 이름을 「제26회 / 광명시장기 / 검도대회」처럼 세 줄로 나눕니다"
DATE_PLACEHOLDER = "비우면 대회 날짜 (예: 2026.04.12)"
TITLE_LINES_HEIGHT = 110


class PhotoCoverEditor(ScreenFitDialog):
    """「저장」을 누르면 OutputBook 에 바로 반영한다(사진을 못 읽으면 알리고 창을 닫지 않는다)."""

    def __init__(self, book: OutputBook, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("표지 고치기")
        self.resize(900, 900)
        self._book = book
        current = book.settings.photo_cover
        self._front = CoverPhotoPicker(PickerText("앞표지 사진", FRONT_HINT), current.photo, book, front=True)
        self._back = CoverPhotoPicker(PickerText("뒤표지 사진", BACK_HINT), current.back_photo, book, front=False)
        self._title_lines = QPlainTextEdit(current.title_lines)
        self._title_lines.setPlaceholderText(TITLE_PLACEHOLDER)
        self._title_lines.setFixedHeight(TITLE_LINES_HEIGHT)
        self._fields = {
            "date_text": QLineEdit(current.date_text),
            "venue": QLineEdit(current.venue),
            "host": QLineEdit(current.host),
            "organizer": QLineEdit(current.organizer),
            "sponsor": QLineEdit(current.sponsor),
        }
        self._fields["date_text"].setPlaceholderText(DATE_PLACEHOLDER)
        self._logo = QLabel()
        self._logo.setObjectName("logoSlot")
        self._logo.setFixedSize(168, 52)
        self._logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("저장")
        buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName("primary")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("취소")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(self._content(), 1)
        layout.addWidget(buttons)
        self._show_logo()

    def _content(self) -> QScrollArea:
        page = QWidget()
        page.setObjectName("page")
        column = QVBoxLayout(page)
        column.setSpacing(12)
        column.addWidget(
            _hint(
                f"내 사진은 「문서 › {self._book.photo_folder().parent.name} › {self._book.photo_folder().name}」 폴더에 넣어 두면 "
                "아래 목록에 함께 나옵니다. "
                "쪽에 맞게 가운데를 잘라 씁니다. 다 만든 표지 파일은 출력 화면의 「앞표지 파일 넣기」「뒤표지 파일 넣기」로 넣습니다."
            )
        )
        column.addWidget(self._front)
        column.addWidget(self._text_card())
        column.addWidget(self._back)
        column.addWidget(self._logo_card())
        column.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(page)
        return scroll

    def _text_card(self) -> QFrame:
        card = _card()
        column = QVBoxLayout(card)
        column.addWidget(_title("표지 글 (자리·글꼴은 고정, 내용만)"))
        form = QFormLayout()
        form.addRow("제목 (줄마다)", self._title_lines)
        form.addRow("날짜", self._fields["date_text"])
        form.addRow("장소", self._fields["venue"])
        form.addRow("주최", self._fields["host"])
        form.addRow("주관", self._fields["organizer"])
        form.addRow("후원", self._fields["sponsor"])
        column.addLayout(form)
        column.addWidget(_hint("주최·주관·후원 칸을 비우면 그 항목은 빠집니다."))
        return card

    def _logo_card(self) -> QFrame:
        pick = button("로고 그림 고르기")
        pick.clicked.connect(self._pick_logo)
        side = QVBoxLayout()
        side.addWidget(_title("뒤표지 왼쪽 아래 광명시 로고"))
        side.addWidget(_hint(LOGO_HINT))
        side.addWidget(pick, 0, Qt.AlignmentFlag.AlignLeft)
        card = _card()
        row = QHBoxLayout(card)
        row.addWidget(self._logo, 0, Qt.AlignmentFlag.AlignTop)
        row.addLayout(side, 1)
        return card

    def _pick_logo(self) -> None:
        path = open_file(self, "광명시 로고 그림 고르기", "", PHOTO_FILTER)
        if path is None:
            return
        try:
            self._book.choose_city_logo(path)
        except ExportError as error:
            report_error(self, error)
            return
        self._show_logo()

    def _show_logo(self) -> None:
        logo = self._book.city_logo()
        if logo is None:
            self._logo.setText("아직 없음")
            return
        pixmap = QPixmap()
        pixmap.loadFromData(logo.png)
        mode, smooth = Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        self._logo.setPixmap(pixmap.scaled(self._logo.width() - 8, self._logo.height() - 8, mode, smooth))

    def _save(self) -> None:
        values = {name: field.text().strip() for name, field in self._fields.items()}
        photo_cover = replace(
            self._book.settings.photo_cover,
            photo=self._front.ref,
            back_photo=self._back.ref,
            title_lines=self._title_lines.toPlainText().strip(),
            **values,
        )
        try:
            self._book.set_photo_cover(photo_cover)
        except ExportError as error:
            report_error(self, error)
            return
        self.accept()


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
