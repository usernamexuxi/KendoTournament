"""여러 부문 대진을 A4 에 위에서부터 채워 싣는다(책자).

쪽 맨 위에는 묶음 제목(「초등부 남자」) 하나만 쓰고, 그 아래로 부문 대진을 차례로 싣는다.
운영자가 새 쪽을 지정하면 새 쪽으로 넘긴다. 한 쪽에 다 안 들어가는 묶음은 가장 적은 쪽 수를
먼저 정하고, 그 쪽 수 안에서 쪽마다 높이가 가장 고르게 나눈다 — 앞쪽부터 꽉 채우면 마지막 쪽에 대진 하나만
외롭게 남아 보기 나쁘다(운영자 지적: 초1~초5 한 쪽, 초6 혼자 한 쪽 → 초1~3 / 초4~6).
한 쪽에 실을 대진이 정해지면 줄 간격을 넓혀 쪽을 채우고, 남는 자리는 대진 사이 여백으로 고르게 나눈다.
한 칸에 도저히 안 들어가는 대진만 절반씩 나눠(bracket_parts) 다른 대진처럼 빈자리에 이어 싣고,
한 묶음이 두 쪽 이상이면 쪽 제목에 번호를 단다: 「성인부 남자 (1)」·「성인부 남자 (2)」(운영자 지시).
한 쪽짜리 묶음은 앞 쪽에 자리가 넉넉하면 가로선 아래에 이어 싣는다(booklet_sheet).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from kendo_tournament.domain.draw.numbering import MatchNode, NumberedBracket
from kendo_tournament.domain.layout.booklet_sheet import (
    CONTENT_BOTTOM,
    CONTENT_TOP,
    PACK_MIN_ROW,
    SUBTITLE_HEIGHT,
    BookletItem,
    Group,
    content_height,
    needed,
    number_pages,
    render_sheet,
    sheet_height,
)
from kendo_tournament.domain.layout.bracket_layout import fits_two_sided, side_rows
from kendo_tournament.domain.layout.bracket_pages import layout_bracket
from kendo_tournament.domain.layout.bracket_parts import remaining_matches, split_parts
from kendo_tournament.domain.layout.primitives import PageLayout

__all__ = ["CONTENT_BOTTOM", "CONTENT_TOP", "BookletItem", "layout_booklet", "page_numbers"]

# 다른 묶음을 이어 실을지 볼 때의 줄 간격. 가장 좁은 줄 간격으로 보면 쪽이 빽빽해진다.
MERGE_ROW = 11.0


@dataclass
class _Run:
    """같은 쪽들에 이어 실을 수 있는 작은 대진 덩어리(같은 묶음, 사이에 새 쪽 지정·큰 대진 없음)."""

    section: str
    items: list[BookletItem] = field(default_factory=list)


def _fits_alone(item: BookletItem) -> bool:
    """세로로 들어가고 양쪽 대진의 이름이 가로로 들어가야 책자 한 칸에 싣는다."""
    if needed([item], PACK_MIN_ROW) > content_height():
        return False
    root = item.numbered.root
    return not isinstance(root, MatchNode) or fits_two_sided(item.bracket, root)


def _part_fits(item: BookletItem, node: MatchNode) -> bool:
    rows = side_rows(node) * item.min_row + SUBTITLE_HEIGHT
    return rows <= content_height() and fits_two_sided(item.bracket, node)


def _parts_of(item: BookletItem) -> list[BookletItem]:
    """한 칸에 넘치는 부문을 조각들로 바꾼다. 들어가면 그대로."""
    root = item.numbered.root
    if not isinstance(root, MatchNode) or _fits_alone(item):
        return [item]
    parts = split_parts(root, lambda node: _part_fits(item, node))
    footer = tuple(remaining_matches(root, parts))
    return [
        BookletItem(
            item.section,
            item.bracket,
            NumberedBracket(part, ()),
            item.new_page and index == 1,
            item,
            footer if index == len(parts) else (),
            item.members,
            item.is_team,
            item.numbers,
        )
        for index, part in enumerate(parts, start=1)
    ]


def _fits(items: list[BookletItem]) -> bool:
    return needed(items, PACK_MIN_ROW) <= content_height()


def _fewest_pages(items: list[BookletItem]) -> int:
    pages, current = 1, [items[0]]
    for item in items[1:]:
        if _fits([*current, item]):
            current.append(item)
        else:
            pages, current = pages + 1, [item]
    return pages


_Best = dict[tuple[int, int], tuple[float, list[int]]]


def _best_cut(items: list[BookletItem], end: int, used: int, best: _Best) -> tuple[float, list[int]] | None:
    """items[:end] 를 used 쪽으로 나눌 때 가장 높은 쪽이 가장 낮은 방법(마지막 쪽이 시작하는 자리들)."""
    options = []
    for start in range(used - 1, end):
        page = items[start:end]
        if (start, used - 1) not in best or not _fits(page):
            continue
        before, cuts = best[(start, used - 1)]
        options.append((max(before, needed(page, PACK_MIN_ROW)), [*cuts, start]))
    return min(options, key=lambda option: option[0]) if options else None


def _even_split(items: list[BookletItem], pages: int) -> list[list[BookletItem]]:
    """순서를 지키며 items 를 pages 쪽으로 나눈다. 가장 높은 쪽이 가장 낮아지게(쪽마다 고르게) 고른다."""
    best: _Best = {(0, 0): (0.0, [])}
    for used in range(1, pages + 1):
        for end in range(used, len(items) + 1):
            found = _best_cut(items, end, used, best)
            if found is not None:
                best[(end, used)] = found
    cuts = [*best[(len(items), pages)][1], len(items)]
    return [items[a:b] for a, b in zip(cuts, cuts[1:], strict=False)]


def _runs(items: list[BookletItem]) -> list[_Run | BookletItem]:
    """큰 대진은 그대로, 작은 대진은 이어 실을 덩어리로 묶는다."""
    parts: list[_Run | BookletItem] = []
    for item in items:
        if item.numbered.root is None:
            continue
        if not _fits_alone(item):
            parts.append(item)
            continue
        last = parts[-1] if parts else None
        if isinstance(last, _Run) and not item.new_page and item.section == last.section:
            last.items.append(item)
        else:
            parts.append(_Run(item.section, [item]))
    return parts


def _sheets(expanded: list[BookletItem]) -> list[tuple[str, list[BookletItem]] | BookletItem]:
    sheets: list[tuple[str, list[BookletItem]] | BookletItem] = []
    for part in _runs(expanded):
        if isinstance(part, BookletItem):
            sheets.append(part)
            continue
        sheets += [(part.section, chunk) for chunk in _even_split(part.items, _fewest_pages(part.items))]
    return sheets


def _can_join(page: list[Group], section: str, chunk: list[BookletItem], pages_of: Counter[str]) -> bool:
    """한 쪽짜리 다른 묶음이 남은 자리에 넉넉히 들어가면 이어 싣는다.

    운영자가 새 쪽을 정했거나, 개인전과 단체전이 한 쪽에 섞이게 되면 안 한다(운영자 지시).
    """
    if not page or chunk[0].new_page or pages_of[section] > 1:
        return False
    if page[-1][1][-1].is_team != chunk[0].is_team:
        return False
    return sheet_height([*page, (section, chunk)], MERGE_ROW) <= content_height()


def _planned(items: list[BookletItem]) -> list[tuple[list[PageLayout], list[BookletItem]]]:
    """(그린 쪽들, 그 쪽들에 실린 부문들) 을 차례로. 큰 대진은 자기 쪽(들), 작은 대진 묶음은 한 쪽씩이다."""
    expanded = [part for original in items for part in _parts_of(original)]
    sheets = _sheets(expanded)
    pages_of = Counter(sheet[0] for sheet in sheets if isinstance(sheet, tuple))
    seen: Counter[str] = Counter()
    planned: list[tuple[list[PageLayout], list[BookletItem]]] = []
    page: list[Group] = []
    for sheet in sheets:
        if isinstance(sheet, BookletItem):
            _flush(page, planned)
            title = f"{sheet.section} · {sheet.bracket.title}"
            planned.append((layout_bracket(sheet.bracket, sheet.numbered, title), [sheet]))
            continue
        section, chunk = sheet
        seen[section] += 1
        header = f"{section} ({seen[section]})" if pages_of[section] > 1 else section
        if not _can_join(page, section, chunk, pages_of):
            _flush(page, planned)
        page.append((header, chunk))
    _flush(page, planned)
    return planned


def _flush(page: list[Group], planned: list[tuple[list[PageLayout], list[BookletItem]]]) -> None:
    if page:
        planned.append(([render_sheet(page)], [item for _, members in page for item in members]))
        page.clear()


def layout_booklet(items: list[BookletItem], first_page: int = 1) -> list[PageLayout]:
    """부문들을 주어진 순서대로 A4 쪽에 싣고 바깥 모서리에 쪽 번호(first_page 부터)를 단다."""
    pages = [page for drawn, _ in _planned(items) for page in drawn]
    number_pages(pages, first_page)
    return pages


def page_numbers(items: list[BookletItem]) -> list[int | None]:
    """items 와 같은 순서로, 각 부문이 실리는 (첫) 쪽 번호. 대진이 비어 안 실리는 부문은 None."""
    first_page: dict[int, int] = {}
    page = 1
    for drawn, members in _planned(items):
        for member in members:
            first_page.setdefault(id(member.source or member), page)
        page += len(drawn)
    return [first_page.get(id(item)) for item in items]
