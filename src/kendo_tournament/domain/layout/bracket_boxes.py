"""대진표 이름 상자: 세 칸(도장 · 이름 · 출전 번호)으로 나눈 상자.

왼쪽 대진은 「도장 | 이름 | 번호」 다음에 선이 나가고, 오른쪽 대진은 거울상(「번호 | 이름 | 도장」)이다.
번호 칸이 선 쪽에 붙어야 몇 번 선수가 어느 경기로 가는지 바로 읽힌다(운영자가 보낸 예시 화면).
도장 칸은 대진 전체에서 가장 긴 도장 이름에 맞춰 폭을 같게 해 칸 경계가 위아래로 줄을 맞춘다.
단체전은 도장 칸 없이 「도장+팀 이름」 하나와 번호 칸이고, 운영자가 켜 두면 상자 바로 밑에 팀원 이름을 작게 쓴다.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from kendo_tournament.domain.layout.bracket_fit import printed_width_mm
from kendo_tournament.domain.layout.primitives import (
    MM_PER_PT,
    Align,
    LineItem,
    PageLayout,
    RectItem,
    TextItem,
    estimated_width_mm,
)
from kendo_tournament.domain.model import Entry

# 운영자가 「딱 좋다」고 한 책자(초1~초3)에서 실제로 쓰인 크기(15.9~16). 다섯 글자 도장 8강이 양쪽 대진에 들도록 조금 낮췄다.
NAME_PT = 15.5
DOJANG_PT = 7.5
BOX_PAD = 1.8
BOX_LINE_PT = 0.6
BOX_MAX_HEIGHT = 8.0
BOX_ROW_RATIO = 0.74
DOJANG_COLOR = "#262626"
DOJANG_FILL = "#fdf8e4"
NUMBER_FILL = "#f2f2f2"
MEMBER_COLOR = "#4a4a4a"
MEMBER_PT = 8.5
MEMBER_GAP = 0.6
ENTRY_NUMBER_PT = 9.0
# 출전 번호는 책자 전체에서 이어지므로 세 자리까지 든다.
NUMBER_CELL = 8.0
ENTRY_NUMBER_COLOR = "#555555"
EDGE_TOLERANCE = 1e-3


@dataclass(frozen=True)
class BoxNotes:
    """이름 상자에 덧붙는 것. members 는 팀 칸 id → 팀원 줄, numbers 는 칸 id → 책자 전체에서 이어지는 출전 번호."""

    members: Mapping[str, str] = field(default_factory=dict)
    numbers: Mapping[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class BoxPlace:
    """상자 하나의 자리(mm). y 는 가운데, dojang_width 는 대진 전체가 같이 쓰는 도장 칸 폭이다."""

    left: float
    y: float
    width: float
    height: float
    dojang_width: float
    mirrored: bool
    slot: int


def spaced(name: str) -> str:
    """책자처럼 이름 글자 사이를 띄운다(「이 유 성」)."""
    return " ".join(name)


def team_text(entry: Entry) -> str:
    return f"{entry.dojang}{entry.name}"


def _dojang_cell(entry: Entry, printed: bool) -> float:
    if entry.team:
        return 0.0
    measure = printed_width_mm if printed else estimated_width_mm
    return measure(entry.dojang, DOJANG_PT) + 2 * BOX_PAD


def _name_cell(entry: Entry, name_pt: float, printed: bool) -> float:
    measure = printed_width_mm if printed else estimated_width_mm
    text = team_text(entry) if entry.team else spaced(entry.name)
    return measure(text, name_pt) + 2 * BOX_PAD


def dojang_column(entries: Iterable[Entry | None]) -> float:
    """대진 전체가 같이 쓰는 도장 칸 폭(mm). 개인 선수가 없으면 0 이다."""
    return max((_dojang_cell(entry, printed=False) for entry in entries if entry is not None), default=0.0)


def boxes_width(entries: Iterable[Entry | None], name_pt: float, printed: bool = False) -> float:
    """세 칸 상자의 폭(mm): 가장 긴 도장 칸 + 가장 긴 이름 칸 + 번호 칸.

    printed 면 PDF 글꼴 폭으로(들어가는지 판단), 아니면 넉넉한 어림으로(배치) 잰다.
    """
    present = [entry for entry in entries if entry is not None]
    if not present:
        return 0.0
    dojang = max(_dojang_cell(entry, printed) for entry in present)
    name = max(_name_cell(entry, name_pt, printed) for entry in present)
    return dojang + name + NUMBER_CELL


def box_height(row: float) -> float:
    return min(BOX_MAX_HEIGHT, row * BOX_ROW_RATIO)


def draw_member_line(page: PageLayout, text: str, place: BoxPlace) -> None:
    """팀 상자 바로 밑, 팀 이름 칸 가운데에 팀원 줄을 쓴다. 칸보다 길면 출력기가 칸 폭에 맞춰 줄인다."""
    _, (left, width), _ = _cells(place, team=True)
    line_y = place.y + place.height / 2 + MEMBER_GAP + MEMBER_PT * MM_PER_PT / 2
    page.texts.append(TextItem(left + width / 2, line_y, text, MEMBER_PT, Align.CENTER, max_width=width, color=MEMBER_COLOR))


def _cells(place: BoxPlace, team: bool) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    """(도장, 이름, 번호) 칸의 (왼쪽 x, 폭). 왼쪽 대진은 도장이 바깥, 오른쪽 대진은 거울상이다."""
    dojang = 0.0 if team else place.dojang_width
    name = place.width - dojang - NUMBER_CELL
    right = place.left + place.width
    if place.mirrored:
        return (right - dojang, dojang), (place.left + NUMBER_CELL, name), (place.left, NUMBER_CELL)
    return (place.left, dojang), (place.left + dojang, name), (right - NUMBER_CELL, NUMBER_CELL)


def _outline(page: PageLayout, place: BoxPlace, dividers: list[float]) -> None:
    top, bottom, right = place.y - place.height / 2, place.y + place.height / 2, place.left + place.width
    page.lines += [
        LineItem(place.left, top, right, top, BOX_LINE_PT),
        LineItem(place.left, bottom, right, bottom, BOX_LINE_PT),
    ]
    page.lines += [LineItem(x, top, x, bottom, BOX_LINE_PT) for x in [place.left, *dividers, right]]


def _dividers(place: BoxPlace, cells: list[tuple[float, float]]) -> list[float]:
    """상자 안쪽 칸 경계의 x. 폭이 0 인 칸(단체전 도장 칸)은 경계를 만들지 않는다."""
    edges = {round(left + width, 6) for left, width in cells if width > 0} | {
        round(left, 6) for left, width in cells if width > 0
    }
    right = place.left + place.width
    return sorted(x for x in edges if place.left + EDGE_TOLERANCE < x < right - EDGE_TOLERANCE)


def _fill(page: PageLayout, place: BoxPlace, cell: tuple[float, float], color: str) -> None:
    left, width = cell
    if width > 0:
        page.rects.append(RectItem(left, place.y - place.height / 2, width, place.height, color))


def draw_name_box(page: PageLayout, entry: Entry, place: BoxPlace, number: int | None) -> None:
    """세 칸 상자를 그린다. 이름 글자에 slot 을 달아 화면에서 칸을 고를 수 있게 한다.

    number 가 없으면(대진 짜기 화면처럼 책자 번호를 아직 안 매긴 곳) 번호 칸은 비워 둔다.
    """
    dojang, name, number_cell = _cells(place, entry.team)
    _fill(page, place, dojang, DOJANG_FILL)
    _fill(page, place, number_cell, NUMBER_FILL)
    _outline(page, place, _dividers(place, [dojang, name, number_cell]))
    text = team_text(entry) if entry.team else spaced(entry.name)
    room = name[1] - 2 * BOX_PAD
    page.texts.append(TextItem(name[0] + name[1] / 2, place.y, text, NAME_PT, Align.CENTER, max_width=room, slot=place.slot))
    if dojang[1] > 0:
        page.texts.append(
            TextItem(
                dojang[0] + dojang[1] / 2,
                place.y,
                entry.dojang,
                DOJANG_PT,
                Align.CENTER,
                bold=True,
                max_width=dojang[1] - 2 * BOX_PAD,
                color=DOJANG_COLOR,
            )
        )
    if number is not None:
        page.texts.append(
            TextItem(
                number_cell[0] + number_cell[1] / 2,
                place.y,
                str(number),
                ENTRY_NUMBER_PT,
                Align.CENTER,
                max_width=NUMBER_CELL - 1.0,
                color=ENTRY_NUMBER_COLOR,
            )
        )
