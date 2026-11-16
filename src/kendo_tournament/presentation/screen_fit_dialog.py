"""화면(작업 표시줄을 뺀 곳) 안에 다 들어오게 여는 대화상자.

크기만 화면 비율로 줄여서는 모자랐다. Qt 는 대화상자를 본 창 가운데에 놓고 제목 줄은 크기에 들어가지 않아,
노트북 배율 150% 에서 아래 「저장」 단추가 작업 표시줄 밑으로 숨었다(운영자 화면에서 실제로 잘림).
그래서 창이 뜬 뒤 제목 줄까지 포함한 바깥 크기로 화면 안에 맞추고 위치도 화면 안으로 옮긴다.
"""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import QDialog, QWidget


class ScreenFitDialog(QDialog):
    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        # 제목 줄 두께는 창이 실제로 그려진 뒤에야 알 수 있어 한 박자 늦게 맞춘다.
        QTimer.singleShot(0, lambda: keep_on_screen(self))


def keep_on_screen(window: QWidget) -> None:
    """제목 줄까지 포함한 창 전체가 화면(작업 표시줄 뺀 곳) 안에 들어오게 줄이고 옮긴다."""
    available = window.screen().availableGeometry()
    frame = window.frameGeometry()
    border_width = frame.width() - window.width()
    border_height = frame.height() - window.height()
    window.resize(
        min(window.width(), available.width() - border_width),
        min(window.height(), available.height() - border_height),
    )
    frame = window.frameGeometry()
    left = min(max(frame.left(), available.left()), available.right() - frame.width() + 1)
    top = min(max(frame.top(), available.top()), available.bottom() - frame.height() + 1)
    window.move(left, top)
