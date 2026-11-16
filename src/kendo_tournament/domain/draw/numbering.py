"""실제로 치르는 경기만 골라 경기 번호를 매긴다.

번호 순서는 개발자가 보낸 대진표 예시를 따른다(spec 6.3). 라운드마다 왼쪽 절반을 위에서 아래로,
이어서 오른쪽 절반을 위에서 아래로 매기고, 결승이 마지막이다. 3위 결정전은 하지 않는다(공동 3위, 개발자 지시).
"""

from __future__ import annotations

from dataclasses import dataclass

from kendo_tournament.domain.draw.bracket import Bracket


@dataclass(frozen=True)
class Leaf:
    slot: int


@dataclass(frozen=True)
class MatchNode:
    number: int
    round: int
    start: int
    length: int
    top: Leaf | MatchNode
    bottom: Leaf | MatchNode


Node = Leaf | MatchNode


@dataclass(frozen=True)
class NumberedBracket:
    root: Node | None
    matches: tuple[MatchNode, ...]

    @property
    def final(self) -> MatchNode | None:
        return self.root if isinstance(self.root, MatchNode) else None


@dataclass(frozen=True)
class _Pending:
    round: int
    start: int
    length: int
    top: Leaf | _Pending
    bottom: Leaf | _Pending


def _collapse(bracket: Bracket, start: int, length: int) -> Leaf | _Pending | None:
    """빈 칸(부전승·기권)을 걷어 낸 경기 나무. 한쪽이 비면 다른 쪽이 그대로 올라간다."""
    if bracket.count_in(start, length) == 0:
        return None
    if length == 1:
        return Leaf(start)
    half = length // 2
    top = _collapse(bracket, start, half)
    bottom = _collapse(bracket, start + half, half)
    if top is None:
        return bottom
    if bottom is None:
        return top
    return _Pending(length.bit_length() - 1, start, length, top, bottom)


def _pending_in(node: Leaf | _Pending | None) -> list[_Pending]:
    if not isinstance(node, _Pending):
        return []
    return _pending_in(node.top) + _pending_in(node.bottom) + [node]


def _numbered(node: Leaf | _Pending, numbers: dict[int, int]) -> Node:
    if isinstance(node, Leaf):
        return node
    return MatchNode(
        numbers[id(node)],
        node.round,
        node.start,
        node.length,
        _numbered(node.top, numbers),
        _numbered(node.bottom, numbers),
    )


def number_matches(bracket: Bracket) -> NumberedBracket:
    root = _collapse(bracket, 0, bracket.size)
    pending = _pending_in(root)
    half = bracket.size // 2
    order = sorted(pending, key=lambda m: (m.round, m.start >= half and m.length < bracket.size, m.start))

    numbers: dict[int, int] = {}
    next_number = 1
    for match in order:
        numbers[id(match)] = next_number
        next_number += 1

    if root is None:
        return NumberedBracket(None, ())
    numbered_root = _numbered(root, numbers)
    matches = sorted(_matches_in(numbered_root), key=lambda m: m.number)
    return NumberedBracket(numbered_root, tuple(matches))


def _matches_in(node: Node) -> list[MatchNode]:
    if isinstance(node, Leaf):
        return []
    return _matches_in(node.top) + _matches_in(node.bottom) + [node]
