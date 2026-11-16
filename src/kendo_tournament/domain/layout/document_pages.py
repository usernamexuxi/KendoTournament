"""끼워 넣을 문서(워드·한글)의 글과 표를 A4 쪽으로 다시 앉힌다.

원본의 글꼴·그림·꾸밈은 한글·워드 프로그램 없이는 그대로 옮길 수 없어(ADR: 한글 비의존) 글과 표만 싣는다.
원본 모양 그대로 넣으려면 PDF 로 저장해서 넣으면 된다.
"""

from __future__ import annotations

from dataclasses import dataclass

from kendo_tournament.domain.layout.primitives import (
    MM_PER_PT,
    PAGE_HEIGHT,
    PAGE_WIDTH,
    Align,
    LineItem,
    PageLayout,
    TextItem,
    estimated_width_mm,
)

MARGIN = 20.0
BODY_PT = 11.0
TABLE_PT = 10.0
LINE_SPACING = 1.6
CELL_PADDING = 1.5
PARAGRAPH_GAP = 2.0
TABLE_GAP = 4.0
GRID_PT = 0.5
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN
BOTTOM = PAGE_HEIGHT - MARGIN


@dataclass(frozen=True)
class DocParagraph:
    text: str


@dataclass(frozen=True)
class DocTable:
    rows: tuple[tuple[str, ...], ...]


DocBlock = DocParagraph | DocTable


def line_height(size_pt: float) -> float:
    return size_pt * MM_PER_PT * LINE_SPACING


def wrap(text: str, width: float, size_pt: float) -> list[str]:
    """어림 너비로 글자 단위 줄바꿈을 한다. 빈 글은 빈 줄 하나."""
    lines: list[str] = []
    current = ""
    for char in text:
        if estimated_width_mm(current + char, size_pt) > width and current:
            lines.append(current)
            current = char.lstrip()
        else:
            current += char
    lines.append(current)
    return lines


class _Flow:
    """위에서 아래로 글을 쌓다가 쪽이 차면 새 쪽을 연다."""

    def __init__(self) -> None:
        self.pages: list[PageLayout] = [PageLayout()]
        self.y = MARGIN

    @property
    def page(self) -> PageLayout:
        return self.pages[-1]

    def ensure(self, height: float) -> None:
        if self.y + height > BOTTOM and self.y > MARGIN:
            self.pages.append(PageLayout())
            self.y = MARGIN

    def paragraph(self, text: str) -> None:
        step = line_height(BODY_PT)
        for line in wrap(text, CONTENT_WIDTH, BODY_PT):
            self.ensure(step)
            self.page.texts.append(TextItem(MARGIN, self.y + step / 2, line, BODY_PT, Align.LEFT))
            self.y += step
        self.y += PARAGRAPH_GAP

    def table(self, rows: tuple[tuple[str, ...], ...]) -> None:
        columns = max((len(row) for row in rows), default=0)
        if columns == 0:
            return
        cell_width = CONTENT_WIDTH / columns
        for row in rows:
            self._table_row(row, columns, cell_width)
        self.y += TABLE_GAP

    def _table_row(self, row: tuple[str, ...], columns: int, cell_width: float) -> None:
        step = line_height(TABLE_PT)
        cells = [wrap(text, cell_width - 2 * CELL_PADDING, TABLE_PT) for text in (*row, *[""] * (columns - len(row)))]
        height = max(len(lines) for lines in cells) * step + 2 * CELL_PADDING
        self.ensure(height)
        top, bottom = self.y, self.y + height
        for index, lines in enumerate(cells):
            left = MARGIN + index * cell_width
            for number, line in enumerate(lines):
                y = top + CELL_PADDING + (number + 0.5) * step
                self.page.texts.append(TextItem(left + CELL_PADDING, y, line, TABLE_PT, Align.LEFT))
        right = MARGIN + columns * cell_width
        self.page.lines += [
            LineItem(MARGIN, top, right, top, GRID_PT),
            LineItem(MARGIN, bottom, right, bottom, GRID_PT),
            *(LineItem(MARGIN + i * cell_width, top, MARGIN + i * cell_width, bottom, GRID_PT) for i in range(columns + 1)),
        ]
        self.y = bottom


def document_pages(blocks: list[DocBlock]) -> list[PageLayout]:
    """문단과 표를 차례로 A4 쪽에 싣는다. 내용이 없으면 빈 목록."""
    if not blocks:
        return []
    flow = _Flow()
    for block in blocks:
        if isinstance(block, DocParagraph):
            flow.paragraph(block.text)
        else:
            flow.table(block.rows)
    return flow.pages
