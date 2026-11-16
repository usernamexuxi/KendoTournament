"""무작위 추첨으로 대진을 만든다. 같은 도장은 최대한 늦게 만나게 흩어 놓는다."""

from __future__ import annotations

import random
from collections.abc import Sequence

from kendo_tournament.domain.draw.bracket import Bracket, bracket_size
from kendo_tournament.domain.draw.validate import DojangOf, default_dojang_of, first_match_conflicts
from kendo_tournament.domain.model import Entry

_MAX_REPAIR_ROUNDS = 200


def spread_order(count: int) -> list[int]:
    """비트 반전 순서. 연속한 번호가 절반·4분의 1 … 구역에 번갈아 놓인다."""
    bits = (count - 1).bit_length()
    return sorted(range(count), key=lambda i: int(format(i, f"0{bits}b")[::-1], 2) if bits else 0)


def _grouped_sequence(entries: Sequence[Entry], rng: random.Random, dojang_of: DojangOf) -> list[Entry]:
    groups: dict[str, list[Entry]] = {}
    for entry in entries:
        groups.setdefault(dojang_of(entry), []).append(entry)
    for members in groups.values():
        rng.shuffle(members)
    ordered = sorted(groups.values(), key=lambda members: (-len(members), rng.random()))
    return [entry for members in ordered for entry in members]


def _filled_slots(start: int, length: int, count: int) -> list[int]:
    """length 칸 가운데 count 명이 앉을 칸. 부전승(상대 없이 올라가는 자리)이 가장 적게 나오도록 고른다.

    빈 칸이 한 갈래에 몰려 있으면 그 갈래 전체가 한 번의 부전승이 된다. 그래서 빈 칸 수를 두 갈래에
    「받아올림 없이」(이진수 자리가 겹치지 않게) 나누면 부전승 수가 빈 칸 수의 이진수 1의 개수로
    가장 적어진다 — 짝수 인원이면 1회전에는 부전승이 없다. 그런 나눔 가운데 두 갈래 인원이 가장 고른 것을 쓴다.
    """
    if count == length:
        return list(range(start, start + length))
    if count == 0:
        return []
    half = length // 2
    empty = length - count
    splits = [(left, empty - left) for left in range(max(0, empty - half), min(empty, half) + 1) if left & (empty - left) == 0]
    left, right = min(splits, key=lambda split: (abs(split[0] - split[1]), split[0]))
    return _filled_slots(start, half, half - left) + _filled_slots(start + half, half, half - right)


def _place(sequence: list[Entry], size: int) -> list[Entry | None]:
    """앉을 칸을 고른 뒤, 퍼짐 순서(비트 반전)로 채운다. 연속한 같은 도장 선수가 절반·4분의 1 … 로 흩어진다."""
    slots: list[Entry | None] = [None] * size
    filled = set(_filled_slots(0, size, len(sequence)))
    order = [slot for slot in spread_order(size) if slot in filled]
    for slot, entry in zip(order, sequence, strict=True):
        slots[slot] = entry
    return slots


def _flip_randomly(slots: list[Entry | None], rng: random.Random) -> list[Entry | None]:
    """각 갈래의 좌우를 무작위로 뒤집는다. 누가 몇 라운드에서 만나는지는 변하지 않는다."""
    result = list(slots)
    block = 2
    while block <= len(result):
        half = block // 2
        for start in range(0, len(result), block):
            if rng.random() < 0.5:
                result[start : start + block] = result[start + half : start + block] + result[start : start + half]
        block *= 2
    return result


def _fuller_half_right(slots: list[Entry | None]) -> list[Entry | None]:
    """사람이 더 많은 절반을 오른쪽(뒤 절반)에 둔다. 누가 몇 라운드에서 만나는지는 변하지 않는다.

    대진표는 왼쪽 위에 부문 이름을 쓰는데, 긴 쪽이 왼쪽이면 이름이 대진에 붙어 보인다(운영자: 「왼오를 바꿔」).
    """
    half = len(slots) // 2
    left = sum(entry is not None for entry in slots[:half])
    right = sum(entry is not None for entry in slots[half:])
    return slots[half:] + slots[:half] if left > right else slots


def _repair_first_matches(bracket: Bracket, rng: random.Random, dojang_of: DojangOf) -> Bracket:
    """첫 경기에서 같은 도장이 붙으면, 새 충돌을 만들지 않는 칸과 맞바꿔 푼다."""
    current = bracket
    for _ in range(_MAX_REPAIR_ROUNDS):
        conflicts = first_match_conflicts(current, dojang_of)
        if not conflicts:
            return current
        _, moving = conflicts[0]
        candidates = [j for j, entry in enumerate(current.slots) if entry is not None and j != moving]
        rng.shuffle(candidates)
        before = len(conflicts)
        for target in candidates:
            slots = list(current.slots)
            slots[moving], slots[target] = slots[target], slots[moving]
            trial = current.with_slots(slots)
            if len(first_match_conflicts(trial, dojang_of)) < before:
                current = trial
                break
        else:
            return current
    return current


def draw_bracket(
    entries: Sequence[Entry],
    title: str,
    seed: int,
    dojang_of: DojangOf = default_dojang_of,
) -> Bracket:
    """같은 seed 면 같은 대진이 나온다. 분리할 수 없는 첫 경기 충돌만 남는다."""
    rng = random.Random(seed)
    size = bracket_size(len(entries))
    slots = _place(_grouped_sequence(entries, rng, dojang_of), size)
    bracket = Bracket(title, tuple(_fuller_half_right(_flip_randomly(slots, rng))), seed)
    return _repair_first_matches(bracket, rng, dojang_of)
