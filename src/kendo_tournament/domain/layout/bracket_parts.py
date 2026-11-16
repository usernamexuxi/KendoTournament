"""고정 글자 크기로 한 장(한 칸)에 도저히 안 들어가는 대진만 절반씩 나눈다.

운영자 지시: 글자를 줄이거나 한쪽 대진으로 바꾸지 말고, 어쩔 수 없을 때만 나눠 조각마다 양쪽 대진으로 그린다.
추첨·경기 번호는 그대로 두고 경기 나무를 잘라 보여 줄 뿐이다. 나눈 것은 맨 위 제목 번호(「… (1)」·「… (2)」)와, 마지막 조각 아래 남은 경기 한 줄씩으로 밝힌다(운영자 지시).
"""

from __future__ import annotations

from collections.abc import Callable

from kendo_tournament.domain.draw.numbering import MatchNode


def split_parts(node: MatchNode, fits: Callable[[MatchNode], bool]) -> list[MatchNode]:
    """fits 를 만족할 때까지 절반씩 나눈 부들(위에서 아래 순서). 하나뿐이면 나누지 않은 것이다."""
    top, bottom = node.top, node.bottom
    if fits(node) or not isinstance(top, MatchNode) or not isinstance(bottom, MatchNode):
        return [node]
    return split_parts(top, fits) + split_parts(bottom, fits)


def remaining_matches(root: MatchNode, parts: list[MatchNode]) -> list[str]:
    """조각 우승자끼리 남은 경기를 번호 순서대로 한 줄씩. 조각은 가운데 굵은 번호로 가리킨다."""
    if len(parts) == 1:
        return []
    lines: list[str] = []
    _winner(root, {id(part) for part in parts}, lines, root)
    return lines


def _winner(node: MatchNode, part_ids: set[int], lines: list[str], root: MatchNode) -> str:
    if id(node) in part_ids:
        return f"{node.number}번 승자"
    assert isinstance(node.top, MatchNode) and isinstance(node.bottom, MatchNode)
    top = _winner(node.top, part_ids, lines, root)
    bottom = _winner(node.bottom, part_ids, lines, root)
    prefix = "결승 " if node is root else ""
    lines.append(f"{prefix}{node.number}번 경기: {top} — {bottom}")
    return f"{node.number}번 승자"


def part_title(title: str, index: int, count: int) -> str:
    return title if count == 1 else f"{title} ({index})"
