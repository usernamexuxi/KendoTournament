"""같은 도장끼리의 대결을 찾는다."""

from __future__ import annotations

from collections.abc import Callable

from kendo_tournament.domain.division.dojang import dojang_key
from kendo_tournament.domain.draw.bracket import Bracket, first_meeting_round
from kendo_tournament.domain.model import Entry

DojangOf = Callable[[Entry], str]


def default_dojang_of(entry: Entry) -> str:
    return dojang_key(entry.dojang)


def is_first_match(bracket: Bracket, i: int, j: int) -> bool:
    """두 칸이 만나는 경기가 양쪽 모두에게 첫 경기인지(각 쪽 하위 대진에 선수가 한 명뿐인지)."""
    round_no = first_meeting_round(i, j)
    half = 1 << (round_no - 1)
    return bracket.count_in(i - i % half, half) == 1 and bracket.count_in(j - j % half, half) == 1


def same_dojang_pairs(bracket: Bracket, dojang_of: DojangOf = default_dojang_of) -> list[tuple[int, int, int]]:
    """같은 도장 선수 쌍마다 (칸 i, 칸 j, 만나는 라운드)."""
    occupied = [(i, dojang_of(e)) for i, e in enumerate(bracket.slots) if e is not None]
    pairs = []
    for a, (i, key_i) in enumerate(occupied):
        for j, key_j in occupied[a + 1 :]:
            if key_i == key_j:
                pairs.append((i, j, first_meeting_round(i, j)))
    return pairs


def first_match_conflicts(bracket: Bracket, dojang_of: DojangOf = default_dojang_of) -> list[tuple[int, int]]:
    """첫 경기에서 같은 도장끼리 붙는 칸 쌍."""
    return [(i, j) for i, j, _ in same_dojang_pairs(bracket, dojang_of) if is_first_match(bracket, i, j)]
