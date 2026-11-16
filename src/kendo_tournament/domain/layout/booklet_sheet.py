"""책자 한 쪽에 싣는 것: 부문(BookletItem)·높이 재기·쪽 그리기.

한 쪽에 묶음이 여럿일 수 있다. 자리가 남으면 다음 묶음을 가로선과 그 묶음 제목 아래에 이어 싣는다
(운영자: 「인원 적으면 한 A4 에 나오게, 별로면 사용자가 다음 장으로 옮기면 된다」 — 「이 부문부터 새 쪽」).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from kendo_tournament.domain.draw.bracket import Bracket
from kendo_tournament.domain.draw.numbering import NumberedBracket
from kendo_tournament.domain.layout.bracket_boxes import BoxNotes
from kendo_tournament.domain.layout.bracket_layout import (
    Frame,
    bracket_rows,
    draw_bracket,
    min_row_height,
)
from kendo_tournament.domain.layout.bracket_style import TAB_HEIGHT, draw_title_tab
from kendo_tournament.domain.layout.primitives import PAGE_WIDTH, Align, PageLayout, TextItem

SIDE_MARGIN = 12.0
CONTENT_TOP = 14.0
# 대진표는 쪽 번호 위에서 끝난다(참고 책자도 내용이 번호보다 위에서 끝난다).
CONTENT_BOTTOM = 273.0
# 쪽 번호 자리·크기·색은 참고 책자(612×859pt) 실측을 A4 로 비례 환산한 값: 바깥 끝에서 54pt, 글자 위끝 804pt, 10pt, 검정 80%.
PAGE_NUMBER_EDGE = 18.5
PAGE_NUMBER_Y = 279.7
PAGE_NUMBER_PT = 10.0
PAGE_NUMBER_COLOR = "#333333"
SUBTITLE_HEIGHT = TAB_HEIGHT + 6.0
SUBTITLE_PT = 14.0
# 부문 띠 아래끝 ↔ 맨 윗 이름 줄 가운데.
SUBTITLE_TO_FIRST_ROW = 9.0
BLOCK_GAP = 8.0
# 글자 크기가 고정이라 줄 간격도 그 글자가 겹치지 않는 높이 밑으로 줄이지 않는다.
PACK_MIN_ROW = min_row_height()
PACK_MAX_ROW = 13.0
MIN_SPARE = 8.0
FOOTER_LINE_HEIGHT = 6.0
FOOTER_PT = 10.0
# 팀원 줄을 싣는 단체전은 상자(최대 8mm) 밑에 팀원 줄이 들어가고도 다음 상자와 떨어지는 줄 간격이 필요하다.
MEMBER_ROW = 12.5
ROW_SEARCH_STEPS = 30


@dataclass(frozen=True)
class BookletItem:
    """책자에 실을 부문 하나. new_page 면 운영자가 이 부문부터 새 쪽으로 넘기라고 한 것이다.

    나눈 조각이면 source 가 원래 부문이고, 마지막 조각의 footer 는 조각 우승자끼리 남은 경기들이다.
    members 는 팀 칸 id → 팀원 줄로, 팀 상자 밑에 싣는다(비어 있으면 팀 이름만). is_team 이면 단체전 부문이다.
    numbers 는 칸 id → 책자 전체에서 이어지는 출전 번호로, 이름 상자 바깥쪽에 쓴다.
    """

    section: str
    bracket: Bracket
    numbered: NumberedBracket
    new_page: bool = False
    source: BookletItem | None = None
    footer: tuple[str, ...] = ()
    members: Mapping[str, str] = field(default_factory=dict)
    is_team: bool = False
    numbers: Mapping[str, int] = field(default_factory=dict)

    @property
    def rows(self) -> int:
        return bracket_rows(self.bracket, self.numbered)

    @property
    def min_row(self) -> float:
        """이 부문을 그릴 수 있는 가장 좁은 줄 간격."""
        return MEMBER_ROW if self.members else PACK_MIN_ROW


Group = tuple[str, list[BookletItem]]


def content_height() -> float:
    return CONTENT_BOTTOM - CONTENT_TOP


def needed(items: list[BookletItem], row: float) -> float:
    """row 줄 간격으로 실을 때의 높이. 팀원 줄이 있는 부문은 row 가 좁아도 제 최소 간격을 쓴다."""
    return sum(item.rows * max(row, item.min_row) for item in items) + _fixed(items)


def _fixed(items: list[BookletItem]) -> float:
    footers = sum(len(item.footer) for item in items) * FOOTER_LINE_HEIGHT
    return len(items) * SUBTITLE_HEIGHT + (len(items) - 1) * BLOCK_GAP + footers


def _widest_row(items: list[BookletItem]) -> float:
    """쪽을 채우는 가장 넓은 줄 간격. 대진 위아래 여백을 MIN_SPARE 씩 먼저 남겨 쪽이 꽉 차도 대진끼리 붙지 않게 한다."""
    room = content_height() - (len(items) + 1) * MIN_SPARE
    low, high = PACK_MIN_ROW, PACK_MAX_ROW
    if needed(items, high) <= room:
        return high
    for _ in range(ROW_SEARCH_STEPS):
        middle = (low + high) / 2
        low, high = (middle, high) if needed(items, middle) <= room else (low, middle)
    return low


def sheet_height(groups: Sequence[Group], row: float) -> float:
    """묶음들을 한 쪽에 row 줄 간격으로 실을 때의 높이. 참고 책자처럼 쪽 제목은 없고 부문 띠만 있다."""
    return needed([item for _, members in groups for item in members], row)


def render_sheet(groups: Sequence[Group]) -> PageLayout:
    """묶음들의 대진을 한 쪽에 위에서부터 싣는다. 대진마다 위에 부문 이름 띠를 단다."""
    page = PageLayout()
    items = [item for _, members in groups for item in members]
    row = _widest_row(items)
    spare = max(0.0, (content_height() - needed(items, row)) / (len(items) + 1))
    y = CONTENT_TOP + spare
    for item in items:
        y = _draw_item(page, item, y, row) + BLOCK_GAP + spare
    return page


def _draw_item(page: PageLayout, item: BookletItem, y: float, row: float) -> float:
    row = max(row, item.min_row)
    top = y + SUBTITLE_HEIGHT
    bottom = top + item.rows * row
    drawn_from = len(page.texts)
    frame = Frame(top, bottom, max_row=row)
    draw_bracket(
        page, item.bracket, item.numbered, frame, is_final=item.source is None, notes=BoxNotes(item.members, item.numbers)
    )
    # 띠는 맨 윗 이름에서 늘 같은 거리에 둔다. 칸 위끝에 맞추면 줄 간격·좌우 높이 차이에 따라 띠와 대진 사이가 들쭉날쭉했다.
    names = [t.y for t in page.texts[drawn_from:] if t.slot is not None]
    tab_top = max(y, min(names, default=top + row / 2) - SUBTITLE_TO_FIRST_ROW - TAB_HEIGHT)
    draw_title_tab(page, item.bracket.title, tab_top)
    for line in item.footer:
        bottom += FOOTER_LINE_HEIGHT
        page.texts.append(TextItem(PAGE_WIDTH / 2, bottom - FOOTER_LINE_HEIGHT / 2, line, FOOTER_PT, Align.CENTER))
    return bottom


def number_pages(pages: list[PageLayout], first: int = 1) -> None:
    """참고 책자처럼 쪽 번호를 바깥 모서리에: 홀수 쪽은 오른쪽 아래, 짝수 쪽은 왼쪽 아래."""
    for number, page in enumerate(pages, start=first):
        if number % 2:
            x, align = PAGE_WIDTH - PAGE_NUMBER_EDGE, Align.RIGHT
        else:
            x, align = PAGE_NUMBER_EDGE, Align.LEFT
        item = TextItem(x, PAGE_NUMBER_Y, str(number), PAGE_NUMBER_PT, align, color=PAGE_NUMBER_COLOR)
        page.texts.append(item)
