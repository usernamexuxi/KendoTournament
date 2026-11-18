"""토너먼트 대진의 칸 구조.

칸(slot)은 2의 거듭제곱 개이고 None 은 빈 칸(부전승)이다. 앞 절반이 대진표 왼쪽, 뒤 절반이 오른쪽이다.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from kendo_tournament.domain.model import Entry


@dataclass(frozen=True)
class Bracket:
    title: str
    slots: tuple[Entry | None, ...]
    seed: int

    def __post_init__(self) -> None:
        size = len(self.slots)
        if size < 1 or size & (size - 1):
            raise ValueError(f"칸 수는 2의 거듭제곱이어야 합니다: {size}")

    @property
    def size(self) -> int:
        return len(self.slots)

    @property
    def rounds(self) -> int:
        return (self.size - 1).bit_length()

    @property
    def entries(self) -> tuple[Entry, ...]:
        return tuple(entry for entry in self.slots if entry is not None)

    def with_slots(self, slots: list[Entry | None]) -> Bracket:
        return replace(self, slots=tuple(slots))

    def with_title(self, title: str) -> Bracket:
        return replace(self, title=title)

    def count_in(self, start: int, length: int) -> int:
        return sum(1 for entry in self.slots[start : start + length] if entry is not None)


def bracket_size(entry_count: int) -> int:
    if entry_count < 1:
        raise ValueError("출전자가 없는 종별은 대진을 만들 수 없습니다.")
    return 1 << (entry_count - 1).bit_length()


def first_meeting_round(i: int, j: int) -> int:
    """칸 i 와 j 가 이기고 올라갔을 때 처음 만나는 라운드(1부터)."""
    if i == j:
        raise ValueError("같은 칸입니다.")
    return (i ^ j).bit_length()


def pass_count(entry_count: int) -> int:
    """부전승(상대 없이 한 라운드를 쉬는) 횟수. 라운드마다 남은 사람이 홀수일 때 한 명이 쉰다.

    추첨은 이 횟수만큼만 부전승을 만든다(draw._filled_slots) — 이보다 적게는 짤 수 없다.
    """
    passes = 0
    remaining = entry_count
    while remaining > 1:
        passes += remaining % 2
        remaining = (remaining + 1) // 2
    return passes
