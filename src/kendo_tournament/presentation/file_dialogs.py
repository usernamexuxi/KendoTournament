"""파일 열기·저장 대화상자. 화면의 70% 크기로 가운데에 띄우고 최소화·최대화·닫기 단추를 단다.

윈도우 기본 대화상자는 부모 창(최대화된 본 창) 크기로 화면을 꽉 채워 열리고 줄이는 단추를 달 수 없어
(운영자 지적), Qt 대화상자를 쓴다. 왼쪽 바로 가기에는 자주 쓰는 폴더를 넣는다.

Qt 대화상자의 칸 폭은 작은 글자 기준이라, 이 프로그램의 큰 글자로는 이름·크기·형식·날짜가 잘린다(운영자 지적).
이름 칸이 남는 폭을 다 쓰고 나머지 칸은 내용만큼 넓히며, 바로 가기 칸도 이름이 보이게 넓힌다.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt, QUrl
from PySide6.QtWidgets import QFileDialog, QHeaderView, QSplitter, QTreeView, QWidget

SCREEN_SHARE = 0.7
SIDEBAR_WIDTH = 230
NAME_COLUMN = 0
_SHORTCUTS = (
    QStandardPaths.StandardLocation.DesktopLocation,
    QStandardPaths.StandardLocation.DocumentsLocation,
    QStandardPaths.StandardLocation.DownloadLocation,
    QStandardPaths.StandardLocation.HomeLocation,
)
_WINDOW_FLAGS = (
    Qt.WindowType.Window
    | Qt.WindowType.WindowTitleHint
    | Qt.WindowType.WindowMinMaxButtonsHint
    | Qt.WindowType.WindowCloseButtonHint
)


def _dialog(parent: QWidget, title: str, folder: str, name_filter: str) -> QFileDialog:
    dialog = QFileDialog(parent, title, folder, name_filter)
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    dialog.setWindowFlags(_WINDOW_FLAGS)
    dialog.setSidebarUrls([QUrl.fromLocalFile(QStandardPaths.writableLocation(place)) for place in _SHORTCUTS])
    screen = parent.screen().availableGeometry()
    width, height = int(screen.width() * SCREEN_SHARE), int(screen.height() * SCREEN_SHARE)
    dialog.resize(width, height)
    dialog.move(screen.x() + (screen.width() - width) // 2, screen.y() + (screen.height() - height) // 2)
    _widen_columns(dialog, width)
    return dialog


def _widen_columns(dialog: QFileDialog, width: int) -> None:
    dialog.setViewMode(QFileDialog.ViewMode.Detail)
    files = dialog.findChild(QTreeView, "treeView")
    if files is not None:
        header = files.header()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(header.fontMetrics().horizontalAdvance("수정한 날짜") + 24)
        for column in range(header.count()):
            mode = QHeaderView.ResizeMode.Stretch if column == NAME_COLUMN else QHeaderView.ResizeMode.ResizeToContents
            header.setSectionResizeMode(column, mode)
    splitter = dialog.findChild(QSplitter, "splitter")
    if splitter is not None:
        splitter.setSizes([SIDEBAR_WIDTH, width - SIDEBAR_WIDTH])


def _chosen(dialog: QFileDialog) -> list[Path]:
    if not dialog.exec():
        return []
    return [Path(name) for name in dialog.selectedFiles()]


def open_files(parent: QWidget, title: str, folder: str, name_filter: str) -> list[Path]:
    """여러 파일을 고른다. 취소하면 빈 목록."""
    dialog = _dialog(parent, title, folder, name_filter)
    dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
    return _chosen(dialog)


def open_file(parent: QWidget, title: str, folder: str, name_filter: str) -> Path | None:
    """파일 하나를 고른다. 취소하면 None."""
    dialog = _dialog(parent, title, folder, name_filter)
    dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
    chosen = _chosen(dialog)
    return chosen[0] if chosen else None


def save_file(parent: QWidget, title: str, suggested: str, name_filter: str, suffix: str) -> Path | None:
    """저장할 경로를 고른다. 확장자를 안 적으면 suffix 를 붙인다. 취소하면 None."""
    dialog = _dialog(parent, title, suggested, name_filter)
    dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
    dialog.setFileMode(QFileDialog.FileMode.AnyFile)
    dialog.setDefaultSuffix(suffix.lstrip("."))
    chosen = _chosen(dialog)
    return chosen[0] if chosen else None
