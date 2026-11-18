"""여러 화면이 같이 쓰는 작은 부품."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from kendo_tournament.presentation.style import SPACING

TABLE_ROW_HEIGHT = 44


def page_layout(page: QWidget, title: str, hint: str) -> QVBoxLayout:
    page.setObjectName("page")
    layout = QVBoxLayout(page)
    layout.setContentsMargins(SPACING * 2, SPACING * 2, SPACING * 2, SPACING * 2)
    layout.setSpacing(SPACING)
    heading = QLabel(title)
    heading.setObjectName("pageTitle")
    explanation = QLabel(hint)
    explanation.setObjectName("hint")
    explanation.setWordWrap(True)
    layout.addWidget(heading)
    layout.addWidget(explanation)
    return layout


def button(text: str, primary: bool = False) -> QPushButton:
    widget = QPushButton(text)
    if primary:
        widget.setObjectName("primary")
    return widget


def button_row(*buttons: QPushButton) -> QHBoxLayout:
    row = QHBoxLayout()
    for item in buttons:
        row.addWidget(item)
    row.addStretch(1)
    return row


def empty_state(text: str) -> QLabel:
    """내용이 없을 때 그 자리를 채우는 큰 안내. 빈 표·빈 칸만 덩그러니 남으면 운영자가 무엇을 할지 모른다."""
    label = QLabel(text)
    label.setObjectName("emptyState")
    label.setWordWrap(True)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label


def warning_label() -> QLabel:
    label = QLabel()
    label.setObjectName("warning")
    label.setWordWrap(True)
    label.hide()
    return label


def show_warnings(label: QLabel, lines: list[str], limit: int = 8) -> None:
    if not lines:
        label.hide()
        return
    shown = lines[:limit]
    if len(lines) > limit:
        shown.append(f"… 외 {len(lines) - limit}건")
    label.setText("\n".join(shown))
    label.show()


def report_error(parent: QWidget, error: Exception) -> None:
    QMessageBox.warning(parent, "확인해 주세요", str(error))
