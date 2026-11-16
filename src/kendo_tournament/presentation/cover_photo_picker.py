"""표지 사진 고르는 칸: 카탈로그 사진과 사진 폴더의 사진을 작은 그림으로 한눈에 늘어놓고 눌러서 고른다.

운영자: 「그림 파일 선택 칸이 아니라 예시가 한눈에 보이는 게 낫다」. 목록에 없는 사진만 「다른 파일에서 고르기」로 연다.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QButtonGroup, QFrame, QGridLayout, QLabel, QToolButton, QVBoxLayout, QWidget

from kendo_tournament.application.output_book import OutputBook, chosen_photo
from kendo_tournament.domain.photo_cover import CoverChoice
from kendo_tournament.domain.ports import ExportError
from kendo_tournament.presentation.file_dialogs import open_file
from kendo_tournament.presentation.widgets import button, button_row, report_error

PHOTO_FILTER = "사진 (*.png *.jpg *.jpeg)"
THUMB = QSize(96, 136)
COLUMNS = 6


@dataclass(frozen=True)
class PickerText:
    title: str
    hint: str


class CoverPhotoPicker(QFrame):
    """ref 는 고른 사진의 설정 값(빈 값 = 카탈로그, 또는 파일 경로)."""

    def __init__(self, text: PickerText, current: str, book: OutputBook, front: bool) -> None:
        super().__init__()
        self.setObjectName("card")
        self._book = book
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._refs: dict[QToolButton, str] = {}
        self._grid = QGridLayout()
        self._grid.setSpacing(6)
        # 남는 폭은 맨 오른쪽 빈 칸이 가져가게 해 사진들이 왼쪽부터 붙어 늘어서게 한다.
        self._grid.setColumnStretch(COLUMNS, 1)
        other = button("다른 파일에서 고르기")
        other.clicked.connect(self._pick_other)
        column = QVBoxLayout(self)
        column.addWidget(_label(text.title, "cardTitle"))
        column.addWidget(_label(text.hint, "hint"))
        column.addLayout(self._grid)
        column.addLayout(button_row(other))
        for choice in (book.cover_choice(front), *self._folder_choices()):
            self._add_tile(choice)
        chosen = chosen_photo(current)
        self._select("" if chosen is None else str(chosen))

    @property
    def ref(self) -> str:
        checked = self._group.checkedButton()
        return self._refs[checked] if checked is not None else ""

    def _folder_choices(self) -> tuple[CoverChoice, ...]:
        try:
            return self._book.folder_choices()
        except ExportError as error:
            # 사진 폴더를 못 열어도 카탈로그·다른 파일은 고를 수 있어야 한다 — 알리고 폴더 사진만 뺀다.
            report_error(self, error)
            return ()

    def _add_tile(self, choice: CoverChoice) -> QToolButton:
        tile = QToolButton()
        tile.setObjectName("coverTile")
        tile.setCheckable(True)
        tile.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        tile.setIcon(QIcon(_thumbnail(choice.path)))
        tile.setIconSize(THUMB)
        tile.setText(choice.label)
        tile.setToolTip(str(choice.path))
        index = len(self._refs)
        self._grid.addWidget(tile, index // COLUMNS, index % COLUMNS, Qt.AlignmentFlag.AlignLeft)
        self._group.addButton(tile)
        self._refs[tile] = choice.ref
        return tile

    def _select(self, ref: str) -> None:
        for tile, known in self._refs.items():
            if known == ref:
                tile.setChecked(True)
                return
        # 예전에 다른 곳에서 고른 사진이면 칸을 하나 더 만들어 고른 채로 보여 준다.
        self._add_tile(CoverChoice(Path(ref).stem, ref, Path(ref))).setChecked(True)

    def _pick_other(self) -> None:
        folder = self._book.photo_folder()
        path = open_file(self, "표지 사진 고르기", str(folder) if folder.is_dir() else "", PHOTO_FILTER)
        if path is not None:
            self._select(str(path))


def _thumbnail(path: Path) -> QPixmap:
    """칸 크기에 꽉 차게 줄이고 가운데를 자른다(표지는 세로라 세로 칸)."""
    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        empty = QPixmap(THUMB)
        empty.fill(Qt.GlobalColor.lightGray)
        return empty
    mode, smooth = Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation
    scaled = pixmap.scaled(THUMB, mode, smooth)
    left, top = (scaled.width() - THUMB.width()) // 2, (scaled.height() - THUMB.height()) // 2
    return scaled.copy(left, top, THUMB.width(), THUMB.height())


def _label(text: str, name: str) -> QWidget:
    label = QLabel(text)
    label.setObjectName(name)
    label.setWordWrap(True)
    return label
