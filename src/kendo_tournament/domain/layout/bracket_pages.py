"""대진 하나를 A4 쪽(들)로 나눈다: 쪽 제목을 달고, 한 쪽에 안 들어가면 부(1부·2부 …)마다 한 쪽씩 그린다.

그리기는 bracket_layout 이, 부 나누기는 bracket_parts 가 한다. 여기서는 몇 쪽에 어떻게 나눌지만 정한다.
"""

from __future__ import annotations

from collections.abc import Callable

from kendo_tournament.domain.draw.bracket import Bracket
from kendo_tournament.domain.draw.numbering import Leaf, MatchNode, NumberedBracket
from kendo_tournament.domain.layout.bracket_layout import (
    FULL_PAGE,
    NOTE_FONT_PT,
    Frame,
    draw_bracket,
    draw_two_sided,
    fits_two_sided,
    max_rows_per_side,
    side_rows,
)
from kendo_tournament.domain.layout.bracket_parts import part_title, remaining_matches, split_parts
from kendo_tournament.domain.layout.bracket_style import draw_title_tab
from kendo_tournament.domain.layout.primitives import PAGE_WIDTH, Align, PageLayout, TextItem

FOOTER_LINE_HEIGHT = 6.0
PAGE_TAB_TOP = 16.0


def new_page(title: str) -> PageLayout:
    """쪽 맨 위 가운데에 부문 이름 띠를 단 빈 쪽(참고 책자 모양)."""
    page = PageLayout()
    draw_title_tab(page, title, PAGE_TAB_TOP)
    return page


def fits_page(bracket: Bracket) -> Callable[[MatchNode], bool]:
    def fits(node: MatchNode) -> bool:
        return fits_two_sided(bracket, node) and side_rows(node) <= max_rows_per_side()

    return fits


def layout_bracket(bracket: Bracket, numbered: NumberedBracket, title: str | None = None) -> list[PageLayout]:
    """대진 하나를 A4 여러 장으로 그린다. 한 장에 다 들어가면 1장이다."""
    heading = title if title is not None else bracket.title
    root = numbered.root
    if root is None:
        return []
    if isinstance(root, Leaf):
        page = new_page(heading)
        draw_bracket(page, bracket, numbered, FULL_PAGE)
        return [page]
    parts = split_parts(root, fits_page(bracket))
    footer = remaining_matches(root, parts)
    pages = []
    for index, part in enumerate(parts, start=1):
        page = new_page(part_title(heading, index, len(parts)))
        lines = footer if index == len(parts) else []
        frame = Frame(FULL_PAGE.top, FULL_PAGE.bottom - len(lines) * FOOTER_LINE_HEIGHT)
        draw_two_sided(page, bracket, part, frame, is_final=len(parts) == 1)
        for number, line in enumerate(lines, start=1):
            y = frame.bottom + (number - 0.5) * FOOTER_LINE_HEIGHT
            page.texts.append(TextItem(PAGE_WIDTH / 2, y, line, NOTE_FONT_PT + 1, Align.CENTER))
        pages.append(page)
    return pages
