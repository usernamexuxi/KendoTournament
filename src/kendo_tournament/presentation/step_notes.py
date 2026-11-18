"""왼쪽 단계 목록의 진행 표시: 단계 이름 밑에 「✓ 313명」「할 차례」를 한 줄 붙인다.

화면 아래 「이전 / 다음」 단추는 두었다가 뺐다 — 왼쪽 목록으로 어디든 갈 수 있어 겹치고, 화면 아래 자리만 차지했다(운영자 지적).
"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtWidgets import QListWidget

from kendo_tournament.application.step_progress import StepNote


def show_step_notes(steps_list: QListWidget, names: Sequence[str], notes: Sequence[StepNote]) -> None:
    """단계 이름 밑에 진행 표시를 한 줄 붙인다. 글이 같으면 다시 쓰지 않는다(목록이 깜박이지 않게)."""
    for row, (name, note) in enumerate(zip(names, notes, strict=True)):
        text = f"{name}\n      {note}" if str(note) else name
        item = steps_list.item(row)
        if item is not None and item.text() != text:
            item.setText(text)
