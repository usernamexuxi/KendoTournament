"""왼쪽 단계 목록의 진행 표시: 단계 이름 밑에 「✓ 313명」을 한 줄 붙인다. 아직 안 한 단계는 이름만 둔다.

화면 아래 「이전 / 다음」 단추는 두었다가 뺐다 — 왼쪽 목록으로 어디든 갈 수 있어 겹치고, 화면 아래 자리만 차지했다(운영자 지적).
"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import QListWidget

from kendo_tournament.application.step_progress import StepNote
from kendo_tournament.presentation.style import FONT_FAMILY, STEP_PT

NOTE_INDENT = "      "
# 항목 안쪽 여백·왼쪽 띠·들여쓰기만큼 뺀다. 대회 이름이 길면 메뉴 폭을 넘어 가로 스크롤 막대가 생겼다.
NOTE_ROOM_PX = 90


def show_step_notes(steps_list: QListWidget, names: Sequence[str], notes: Sequence[StepNote]) -> None:
    """단계 이름 밑에 진행 표시를 한 줄 붙인다. 메뉴 폭보다 길면 「…」로 줄인다. 글이 같으면 다시 쓰지 않는다(깜박임 방지)."""
    steps_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    metrics = QFontMetrics(QFont(FONT_FAMILY, STEP_PT))
    room = max(steps_list.viewport().width() - NOTE_ROOM_PX, 0)
    for row, (name, note) in enumerate(zip(names, notes, strict=True)):
        shown = metrics.elidedText(str(note), Qt.TextElideMode.ElideRight, room)
        text = f"{name}\n{NOTE_INDENT}{shown}" if str(note) else name
        item = steps_list.item(row)
        if item is not None and item.text() != text:
            item.setText(text)
