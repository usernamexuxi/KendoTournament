"""③ 부문 화면의 「부전승 점검」: 합치면 부전승이 주는 짝을 추천하고 단추 한 번에 합친다.

합쳐도 줄지 않는 부문은 한 줄로 모아 「그대로 두어도 됩니다」로만 알린다 — 글자로 다 늘어놓으면 읽히지 않는다(운영자 지적).
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QGroupBox, QLabel, QVBoxLayout, QWidget

from kendo_tournament.domain.division.bye_notice import ByeReport, MergeAdvice
from kendo_tournament.presentation.widgets import button, button_row

NO_BYES = "부전승이 생기는 종별이 없습니다. 모든 종별이 1회전부터 빠짐없이 경기합니다."
WHY = "부전승은 인원이 2·4·8·16·32명이 아니면 생깁니다. 아래 추천대로 이웃 학년과 합치면 부전승이 줄어듭니다."
KEEP_HEAD = "그대로 두어도 되는 종별 (이웃과 합쳐도 부전승이 줄지 않음)"
NO_MERGE = "합쳐서 부전승이 주는 종별이 없습니다. 그대로 진행하면 됩니다."


def _advice_text(advice: MergeAdvice) -> str:
    first, second = advice.first, advice.second
    result = "부전승 없음" if advice.after == 0 else f"부전승 {advice.after}번"
    return (
        f"{first.label} {first.count}{first.unit}  +  {second.label} {second.count}{second.unit}"
        f"   →   {advice.merged_count}{first.unit} · 부전승 {advice.before}번 → {result}"
    )


class ByePanel(QGroupBox):
    """merge_requested 는 합칠 부문 이름 묶음들(list[list[str]])을 보낸다."""

    merge_requested = Signal(list)

    def __init__(self) -> None:
        super().__init__("부전승 점검")
        self._layout = QVBoxLayout(self)
        self._content = QWidget()
        self._layout.addWidget(self._content)

    def show_report(self, report: ByeReport) -> None:
        self._layout.removeWidget(self._content)
        self._content.deleteLater()
        self._content = QWidget()
        column = QVBoxLayout(self._content)
        column.setContentsMargins(0, 0, 0, 0)
        if not report.has_byes:
            column.addWidget(_hint(NO_BYES))
        else:
            column.addWidget(_hint(WHY))
            column.addLayout(self._merge_rows(report.merges))
            if report.keep:
                column.addWidget(_hint(KEEP_HEAD))
                column.addWidget(_hint("  ·  ".join(f"{s.label} {s.count}{s.unit} (부전승 {s.passes}번)" for s in report.keep)))
        self._layout.addWidget(self._content)

    def _merge_rows(self, merges: tuple[MergeAdvice, ...]) -> QVBoxLayout:
        rows = QVBoxLayout()
        if not merges:
            rows.addWidget(_hint(NO_MERGE))
            return rows
        rows.addWidget(QLabel(f"추천 {len(merges)}건 — 합치면 부전승이 줄어듭니다"))
        grid = QGridLayout()
        grid.setColumnStretch(0, 1)
        for row, advice in enumerate(merges):
            text = QLabel(_advice_text(advice))
            text.setWordWrap(True)
            merge = button("합치기")
            merge.clicked.connect(lambda _=False, labels=list(advice.labels): self.merge_requested.emit([labels]))
            grid.addWidget(text, row, 0)
            grid.addWidget(merge, row, 1)
        rows.addLayout(grid)
        if len(merges) > 1:
            every = button("추천 모두 합치기", primary=True)
            every.clicked.connect(lambda: self.merge_requested.emit([list(advice.labels) for advice in merges]))
            rows.addLayout(button_row(every))
        return rows


def _hint(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("hint")
    label.setWordWrap(True)
    return label
