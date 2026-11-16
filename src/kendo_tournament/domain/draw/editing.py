"""대진을 손으로 고친다. 고친 칸 말고는 그대로 둔다."""

from __future__ import annotations

from kendo_tournament.domain.draw.bracket import Bracket, first_meeting_round
from kendo_tournament.domain.draw.validate import DojangOf, default_dojang_of, first_match_conflicts
from kendo_tournament.domain.model import Entry


def _check_index(bracket: Bracket, index: int) -> None:
    if not 0 <= index < bracket.size:
        raise IndexError(f"없는 칸입니다: {index}")


def swap_slots(bracket: Bracket, i: int, j: int) -> Bracket:
    _check_index(bracket, i)
    _check_index(bracket, j)
    slots = list(bracket.slots)
    slots[i], slots[j] = slots[j], slots[i]
    return bracket.with_slots(slots)


def withdraw(bracket: Bracket, index: int) -> Bracket:
    """기권한 칸을 비운다. 그 상대는 부전승으로 올라간다."""
    _check_index(bracket, index)
    if bracket.slots[index] is None:
        raise ValueError("이미 빈 칸입니다.")
    slots = list(bracket.slots)
    slots[index] = None
    return bracket.with_slots(slots)


def insert_entry(bracket: Bracket, index: int, entry: Entry) -> Bracket:
    """늦게 신청한 선수를 빈 칸(부전승 자리)에 넣는다."""
    _check_index(bracket, index)
    if bracket.slots[index] is not None:
        raise ValueError("빈 칸에만 넣을 수 있습니다.")
    if any(existing is not None and existing.id == entry.id for existing in bracket.slots):
        raise ValueError("이미 대진에 있는 선수입니다.")
    slots = list(bracket.slots)
    slots[index] = entry
    return bracket.with_slots(slots)


def recommend_insert_slots(bracket: Bracket, entry: Entry, dojang_of: DojangOf = default_dojang_of) -> list[int]:
    """넣을 수 있는 빈 칸을 좋은 순서로 돌려준다.

    첫 경기 충돌이 없는 칸, 같은 도장과 늦게 만나는 칸이 앞에 온다. 빈 칸이 없으면 빈 목록이다.
    """
    key = dojang_of(entry)
    same = [i for i, e in enumerate(bracket.slots) if e is not None and dojang_of(e) == key]

    def score(index: int) -> tuple[int, int]:
        trial = insert_entry(bracket, index, entry)
        conflicts = len(first_match_conflicts(trial, dojang_of))
        earliest = min((first_meeting_round(index, j) for j in same), default=bracket.rounds + 1)
        return (conflicts, -earliest)

    empty = [i for i, e in enumerate(bracket.slots) if e is None]
    return sorted(empty, key=score)
