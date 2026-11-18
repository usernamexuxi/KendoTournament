"""대진표를 A4 위 좌표(mm)로 바꾼다. 화면 미리보기·PDF 가 모두 이 결과를 그린다.

모양은 개발자가 보낸 「남자 단부 개인전 B조」 예시를 따른다(spec 6.3).
왼쪽은 「(도장) 이름」 다음에 선, 오른쪽은 거울상, 결승은 가운데이고 번호는 경기 번호뿐이다.
글자 크기는 인원과 상관없이 늘 BRACKET_FONT_PT 다(운영자 지시: 내용이 많아져도 글씨가 작아지면 안 된다).
인원에 맞춰 바뀌는 것은 줄 간격·이름 칸 너비뿐이고, 그래도 안 들어가면 그때만 나눈다(bracket_parts).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from kendo_tournament.domain.draw.bracket import Bracket
from kendo_tournament.domain.draw.numbering import Leaf, MatchNode, Node, NumberedBracket
from kendo_tournament.domain.layout.bracket_boxes import (
    NAME_PT,
    BoxNotes,
    BoxPlace,
    box_height,
    boxes_width,
    dojang_column,
    draw_member_line,
    draw_name_box,
)
from kendo_tournament.domain.layout.bracket_fit import MIN_ROUND_STEP, label_room
from kendo_tournament.domain.layout.bracket_style import FINAL_WIDTH, draw_final_label
from kendo_tournament.domain.layout.primitives import (
    MM_PER_PT,
    PAGE_HEIGHT,
    PAGE_WIDTH,
    Align,
    LineItem,
    PageLayout,
    TextItem,
)

__all__ = [
    "PAGE_HEIGHT",
    "PAGE_WIDTH",
    "BRACKET_FONT_PT",
    "Align",
    "Frame",
    "LineItem",
    "PageLayout",
    "TextItem",
    "bracket_rows",
    "draw_bracket",
]

SIDE_MARGIN = 12.0
AREA_TOP = 32.0
AREA_BOTTOM = 280.0
FINAL_HALF_WIDTH = 18.0
# 회전이 많아 이름 칸이 모자라면 나누기 전에 결승선부터 이만큼까지 줄인다(운영자: 「그냥 합쳐도 되는 거 아님?」).
MIN_FINAL_HALF_WIDTH = 10.0
MAX_ROUND_STEP = 26.0
MAX_ROW_HEIGHT = 34.0
BRACKET_FONT_PT = NAME_PT
TITLE_FONT_PT = 20.0
# 경기 번호는 이름보다 작게(운영자: 「숫자가 크다」). 이름과 같은 크기면 번호가 이름처럼 눈에 띈다.
MATCH_NUMBER_PT = 12.0
NOTE_FONT_PT = 9.0
LINE_SPACING = 1.7
NUMBER_GAP = 1.4
LABEL_MIN_WIDTH = 30.0
LABEL_MAX_WIDTH = 72.0
RULE_WIDTH_PT = 0.6
SPAN_TOLERANCE = 1e-9
ANCHOR_TOLERANCE = 1e-6


@dataclass(frozen=True)
class Frame:
    """대진을 그릴 세로 구간(mm). 한 장 전체일 수도, 책자의 한 칸일 수도 있다."""

    top: float
    bottom: float
    max_row: float = MAX_ROW_HEIGHT

    @property
    def height(self) -> float:
        return self.bottom - self.top


FULL_PAGE = Frame(AREA_TOP, AREA_BOTTOM)


def min_row_height() -> float:
    return BRACKET_FONT_PT * MM_PER_PT * LINE_SPACING


def max_rows_per_side() -> int:
    return int((AREA_BOTTOM - AREA_TOP) / min_row_height())


def entry_label(bracket: Bracket, slot: int, mirrored: bool) -> str:
    entry = bracket.slots[slot]
    if entry is None:
        return ""
    return f"{entry.name} ({entry.dojang})" if mirrored else f"({entry.dojang}) {entry.name}"


def leaves_of(node: Node) -> list[Leaf]:
    if isinstance(node, Leaf):
        return [node]
    return leaves_of(node.top) + leaves_of(node.bottom)


def _node_y(node: Node, leaf_y: dict[int, float]) -> float:
    if isinstance(node, Leaf):
        return leaf_y[node.slot]
    return (_node_y(node.top, leaf_y) + _node_y(node.bottom, leaf_y)) / 2


@dataclass(frozen=True)
class _Geometry:
    row: float
    font: float
    label_width: float
    dojang_width: float


def _longest_label(bracket: Bracket, leaves: list[Leaf], printed: bool = False) -> float:
    """가장 넓은 이름 상자의 폭(mm)."""
    return boxes_width((bracket.slots[leaf.slot] for leaf in leaves), BRACKET_FONT_PT, printed)


def _geometry(bracket: Bracket, sides: list[list[Leaf]], frame: Frame, room: float = LABEL_MAX_WIDTH) -> _Geometry:
    """가장 긴 쪽 인원으로 줄 간격을, 가장 긴 이름표로 이름 칸 너비를 정한다. 글자 크기는 고정이다."""
    rows = max(len(side) for side in sides)
    row = min(frame.max_row, frame.height / rows)
    every = [leaf for side in sides for leaf in side]
    label = min(room, max(LABEL_MIN_WIDTH, min(LABEL_MAX_WIDTH, _longest_label(bracket, every))))
    return _Geometry(row, BRACKET_FONT_PT, label, dojang_column(bracket.slots[leaf.slot] for leaf in every))


def _two_sided_room(final: MatchNode) -> float:
    return label_room(PAGE_WIDTH / 2 - MIN_FINAL_HALF_WIDTH - SIDE_MARGIN, final.round - 1)


def side_rows(node: MatchNode) -> int:
    """쪽 나눔·책자 자리 계산에 쓰는 줄 수.

    그리기는 두 쪽을 같은 높이로 펴서(_spread_rows) 더 긴 쪽 인원만큼만 쓰지만, 이 값은 예전 방식(준결승 승자
    높이를 맞추느라 한쪽을 옮긴 만큼까지 센 줄 수)을 그대로 둔다. 운영자가 정한 쪽 나눔 기준(40명 이상 두 쪽,
    32명까지 한 쪽)이 그리기 모양을 바꿨다는 이유로 조용히 달라지지 않게 하려는 것이다.
    """
    rows = max(len(leaves_of(node.top)), len(leaves_of(node.bottom)))
    unit = Frame(0.0, float(rows))
    left = _leaf_rows(leaves_of(node.top), 1.0, unit)
    right = _leaf_rows(leaves_of(node.bottom), 1.0, unit)
    delta = (_node_y(node.top, left) - _node_y(node.bottom, right)) / 2
    every = [y - delta for y in left.values()] + [y + delta for y in right.values()]
    return math.ceil(max(every) - min(every) + 1 - SPAN_TOLERANCE)


def _two_sided_geometry(bracket: Bracket, final: MatchNode, frame: Frame) -> _Geometry:
    return _geometry(bracket, [leaves_of(final.top), leaves_of(final.bottom)], frame, _two_sided_room(final))


def _leaf_rows(leaves: list[Leaf], row: float, frame: Frame) -> dict[int, float]:
    top = frame.top + (frame.height - row * len(leaves)) / 2
    return {leaf.slot: top + (i + 0.5) * row for i, leaf in enumerate(leaves)}


def _shifted(rows: dict[int, float], delta: float) -> dict[int, float]:
    return {slot: y + delta for slot, y in rows.items()}


@dataclass
class _Side:
    """한쪽 절반을 그린다. mirrored 면 오른쪽(거울상)이다."""

    bracket: Bracket
    page: PageLayout
    mirrored: bool
    label_edge: float
    step: float
    leaf_y: dict[int, float]
    geometry: _Geometry
    top_round: int
    notes: BoxNotes = field(default_factory=BoxNotes)

    def x_of(self, round_no: int) -> float:
        offset = round_no * self.step
        return self.label_edge - offset if self.mirrored else self.label_edge + offset

    def _text(self, x: float, y: float, text: str, size: float, **extra) -> None:
        gap = NUMBER_GAP if self.mirrored else -NUMBER_GAP
        align = Align.LEFT if self.mirrored else Align.RIGHT
        self.page.texts.append(TextItem(x + gap, y, text, size, align, **extra))

    def draw(self, node: Node, anchor: float | None = None) -> tuple[float, float]:
        """노드를 그리고 (x, y) 를 돌려준다. 부모는 이 점에서 가로선을 시작한다.

        anchor 는 이 쪽 맨 끝 경기(준결승)의 결승선 높이다. 번호와 나가는 선을 그 높이에 두고, 세로선이 거기까지
        닿지 않으면 늘인다 — 고르게 퍼진 쪽은 세로선 가운데가 정가운데와 조금 다를 수 있다.
        """
        if isinstance(node, Leaf):
            y = self.leaf_y[node.slot]
            entry = self.bracket.slots[node.slot]
            width = self.geometry.label_width
            left = self.label_edge if self.mirrored else self.label_edge - width
            if entry is not None:
                height = box_height(self.geometry.row)
                place = BoxPlace(left, y, width, height, self.geometry.dojang_width, self.mirrored, node.slot)
                draw_name_box(self.page, entry, place, self.notes.numbers.get(entry.id))
                if entry.id in self.notes.members:
                    draw_member_line(self.page, self.notes.members[entry.id], place)
            if anchor is not None and abs(anchor - y) > ANCHOR_TOLERANCE:
                self.page.lines.append(LineItem(self.label_edge, y, self.label_edge, anchor))
            return self.label_edge, y if anchor is None else anchor
        # 맨 끝 경기(준결승)는 회전 수가 적은 쪽도 결승 바로 옆 칸에 둔다. 제 회전 칸에 두면 양쪽 준결승선이
        # 가운데에서 다른 거리에 서서 「결승전」이 한쪽으로 치우쳐 보인다(사용자 지적).
        x = self.x_of(self.top_round if anchor is not None else node.round)
        top_x, top_y = self.draw(node.top)
        bottom_x, bottom_y = self.draw(node.bottom)
        self.page.lines += [
            LineItem(top_x, top_y, x, top_y),
            LineItem(bottom_x, bottom_y, x, bottom_y),
            LineItem(x, top_y, x, bottom_y),
        ]
        mid = (top_y + bottom_y) / 2 if anchor is None else anchor
        if not min(top_y, bottom_y) <= mid <= max(top_y, bottom_y):
            self.page.lines.append(LineItem(x, mid, x, min((top_y, bottom_y), key=lambda y: abs(y - mid))))
        self._text(x, mid, str(node.number), MATCH_NUMBER_PT)
        return x, mid


def _spread_rows(final: MatchNode, row: float, frame: Frame) -> tuple[dict[int, float], dict[int, float], float]:
    """두 쪽이 같은 높이를 쓰고, 인원이 적은 쪽은 그 높이에 고르게 퍼진다. 셋째 값은 결승선 높이(가운데)다.

    참고 책자(제26회 광명시장기 카탈로그)는 어느 대진이든 「결승전」이 정가운데에 온다. 예전에는 양쪽 준결승 승자의
    높이만 맞춰서, 인원이 다른 쪽(5명 = 2:3, 25명 = 12:13)은 한쪽이 위로 몰리고 「결승전」이 가운데에서 벗어났다.
    """
    span = row * max(len(leaves_of(final.top)), len(leaves_of(final.bottom)))
    top = frame.top + (frame.height - span) / 2

    def spread(leaves: list[Leaf]) -> dict[int, float]:
        gap = span / len(leaves)
        return {leaf.slot: top + (i + 0.5) * gap for i, leaf in enumerate(leaves)}

    return spread(leaves_of(final.top)), spread(leaves_of(final.bottom)), top + span / 2


def draw_two_sided(
    page: PageLayout,
    bracket: Bracket,
    final: MatchNode,
    frame: Frame,
    is_final: bool = True,
    notes: BoxNotes | None = None,
) -> None:
    """final 을 가운데 경기로 하는 양쪽 대진. is_final 이면 가운데에 번호 대신 「결승전」을 단다(참고 책자).

    notes 는 상자에 덧붙는 팀원 줄(팀 상자 밑)과 출전 번호(상자 바깥쪽)다.
    """
    center = PAGE_WIDTH / 2
    geometry = _two_sided_geometry(bracket, final, frame)
    side_rounds = final.round - 1
    available = center - SIDE_MARGIN - geometry.label_width
    final_half = max(MIN_FINAL_HALF_WIDTH, min(FINAL_HALF_WIDTH, available - side_rounds * MIN_ROUND_STEP))
    room = available - final_half
    # 인원이 적을 때 한 회전 폭을 쪽 끝까지 늘이면 선만 길고 경기 번호가 가운데에 몰린다. 폭을 묶고 가운데로 모은다.
    step = min(MAX_ROUND_STEP, room / max(1, side_rounds))
    left_edge = center - final_half - side_rounds * step
    right_edge = center + final_half + side_rounds * step
    left_rows, right_rows, ly = _spread_rows(final, geometry.row, frame)
    left = _Side(bracket, page, False, left_edge, step, left_rows, geometry, side_rounds, notes or BoxNotes())
    right = _Side(bracket, page, True, right_edge, step, right_rows, geometry, side_rounds, notes or BoxNotes())
    lx, _ = left.draw(final.top, ly)
    rx, _ = right.draw(final.bottom, ly)
    if is_final:
        page.lines += [LineItem(lx, ly, center - FINAL_WIDTH / 2, ly), LineItem(center + FINAL_WIDTH / 2, ly, rx, ly)]
        draw_final_label(page, center, ly)
        return
    page.lines.append(LineItem(lx, ly, rx, ly))
    number_y = ly + MATCH_NUMBER_PT * MM_PER_PT * 1.3
    page.texts.append(TextItem(center, number_y, str(final.number), MATCH_NUMBER_PT, Align.CENTER))


def fits_two_sided(bracket: Bracket, node: MatchNode) -> bool:
    """고정 글자 크기의 가장 긴 이름표(실제 인쇄 폭)가 회전 간격을 떼고 남은 폭에 드는가. 안 들면 나눈다."""
    return _longest_label(bracket, leaves_of(node), printed=True) <= _two_sided_room(node)


def bracket_rows(bracket: Bracket, numbered: NumberedBracket) -> int:
    """대진 하나가 세로로 차지하는 줄 수(양쪽 대진이면 더 긴 쪽). 책자에서 자리를 나눌 때 쓴다."""
    root = numbered.root
    if root is None or isinstance(root, Leaf):
        return 1
    return side_rows(root)


def draw_bracket(
    page: PageLayout,
    bracket: Bracket,
    numbered: NumberedBracket,
    frame: Frame,
    is_final: bool = True,
    notes: BoxNotes | None = None,
) -> None:
    """대진 하나를 쪽의 frame 구간 안에 그린다. notes 는 draw_two_sided 와 같다."""
    root = numbered.root
    if root is None:
        return
    if isinstance(root, Leaf):
        label = f"단독 출전: {entry_label(bracket, root.slot, mirrored=True)}"
        page.texts.append(TextItem(PAGE_WIDTH / 2, (frame.top + frame.bottom) / 2, label, BRACKET_FONT_PT, Align.CENTER))
    else:
        draw_two_sided(page, bracket, root, frame, is_final, notes)
