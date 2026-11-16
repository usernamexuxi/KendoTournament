"""대진표 이름 상자: 참고 책자(광명시장기 카탈로그) 모양.

개인전은 상자 안에 작은 도장 이름과 큰 선수 이름(글자 사이를 띄움)을 쓰고, 오른쪽 대진은 거울상이다.
단체전은 「도장+팀 이름」 하나만 가운데에 쓰고, 운영자가 켜 두면 상자 바로 밑에 팀원 이름을 작게 쓴다.
선은 상자 끝에서 나간다.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from kendo_tournament.domain.layout.bracket_fit import printed_width_mm
from kendo_tournament.domain.layout.primitives import MM_PER_PT, Align, LineItem, PageLayout, TextItem, estimated_width_mm
from kendo_tournament.domain.model import Entry

# 운영자가 「딱 좋다」고 한 책자(초1~초3)에서 실제로 쓰인 크기(15.9~16). 다섯 글자 도장 8강이 양쪽 대진에 들도록 조금 낮췄다.
NAME_PT = 15.5
DOJANG_PT = 7.5
BOX_PAD = 1.8
NAME_GAP = 2.5
BOX_LINE_PT = 0.6
BOX_MAX_HEIGHT = 8.0
BOX_ROW_RATIO = 0.74
DOJANG_COLOR = "#4a4a4a"
MEMBER_PT = 8.5
MEMBER_GAP = 0.6
ENTRY_NUMBER_PT = 9.0
ENTRY_NUMBER_GAP = 1.5
ENTRY_NUMBER_COLOR = "#555555"


@dataclass(frozen=True)
class BoxNotes:
    """이름 상자에 덧붙는 것. members 는 팀 칸 id → 팀원 줄, numbers 는 칸 id → 책자 전체에서 이어지는 출전 번호."""

    members: Mapping[str, str] = field(default_factory=dict)
    numbers: Mapping[str, int] = field(default_factory=dict)


def spaced(name: str) -> str:
    """책자처럼 이름 글자 사이를 띄운다(「이 유 성」)."""
    return " ".join(name)


def team_text(entry: Entry) -> str:
    return f"{entry.dojang}{entry.name}"


def box_width(entry: Entry | None, name_pt: float, printed: bool = False) -> float:
    """상자 폭(mm). printed 면 PDF 글꼴 폭으로(들어가는지 판단), 아니면 넉넉한 어림으로(배치) 잰다."""
    if entry is None:
        return 0.0
    measure = printed_width_mm if printed else estimated_width_mm
    if entry.team:
        return measure(team_text(entry), name_pt) + 2 * BOX_PAD
    content = measure(entry.dojang, DOJANG_PT) + NAME_GAP + measure(spaced(entry.name), name_pt)
    return content + 2 * BOX_PAD


def box_height(row: float) -> float:
    return min(BOX_MAX_HEIGHT, row * BOX_ROW_RATIO)


def draw_member_line(page: PageLayout, text: str, box: tuple[float, float, float, float]) -> None:
    """팀 상자(box) 바로 밑, 상자 가운데에 팀원 줄을 쓴다. 상자보다 길면 출력기가 상자 폭에 맞춰 줄인다."""
    left, y, width, height = box
    line_y = y + height / 2 + MEMBER_GAP + MEMBER_PT * MM_PER_PT / 2
    page.texts.append(TextItem(left + width / 2, line_y, text, MEMBER_PT, Align.CENTER, max_width=width, color=DOJANG_COLOR))


def draw_entry_number(page: PageLayout, number: int, box: tuple[float, float, float, float], mirrored: bool) -> None:
    """상자 바깥쪽(왼쪽 대진은 왼쪽, 오른쪽 대진은 오른쪽)에 출전 번호를 작게 쓴다."""
    left, y, width, _ = box
    if mirrored:
        page.texts.append(
            TextItem(left + width + ENTRY_NUMBER_GAP, y, str(number), ENTRY_NUMBER_PT, Align.LEFT, color=ENTRY_NUMBER_COLOR)
        )
    else:
        page.texts.append(
            TextItem(left - ENTRY_NUMBER_GAP, y, str(number), ENTRY_NUMBER_PT, Align.RIGHT, color=ENTRY_NUMBER_COLOR)
        )


def draw_name_box(page: PageLayout, entry: Entry, box: tuple[float, float, float, float], mirrored: bool, slot: int) -> None:
    """box = (왼쪽 x, 가운데 y, 폭, 높이). 이름 글자에 slot 을 달아 화면에서 칸을 고를 수 있게 한다."""
    left, y, width, height = box
    top, bottom, right = y - height / 2, y + height / 2, left + width
    page.lines += [
        LineItem(left, top, right, top, BOX_LINE_PT),
        LineItem(left, bottom, right, bottom, BOX_LINE_PT),
        LineItem(left, top, left, bottom, BOX_LINE_PT),
        LineItem(right, top, right, bottom, BOX_LINE_PT),
    ]
    room = width - 2 * BOX_PAD
    if entry.team:
        page.texts.append(TextItem(left + width / 2, y, team_text(entry), NAME_PT, Align.CENTER, max_width=room, slot=slot))
        return
    name = spaced(entry.name)
    dojang_room = room - NAME_GAP - estimated_width_mm(name, NAME_PT)
    if mirrored:
        page.texts.append(TextItem(left + BOX_PAD, y, name, NAME_PT, Align.LEFT, max_width=room, slot=slot))
        dojang = TextItem(right - BOX_PAD, y, entry.dojang, DOJANG_PT, Align.RIGHT, max_width=dojang_room, color=DOJANG_COLOR)
    else:
        page.texts.append(TextItem(right - BOX_PAD, y, name, NAME_PT, Align.RIGHT, max_width=room, slot=slot))
        dojang = TextItem(left + BOX_PAD, y, entry.dojang, DOJANG_PT, Align.LEFT, max_width=dojang_room, color=DOJANG_COLOR)
    page.texts.append(dojang)
