"""부전승 점검: 부전승이 생기는 부문을 모으고, 이웃 학년과 합치면 부전승이 주는 짝을 추천한다.

합치기는 운영자가 정한다(추천 옆 「합치기」 단추). 여기서는 추천만 하고 부문을 바꾸지 않는다.
한 부문은 추천 하나에만 든다 — 두 추천이 같은 부문을 쓰면 하나를 합친 뒤 다른 추천이 틀어진다.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from kendo_tournament.domain.draw.bracket import pass_count
from kendo_tournament.domain.model import ELEMENTARY_LAST, HIGH_LAST, MIDDLE_LAST, Event, Gender


@dataclass(frozen=True)
class DivisionSize:
    label: str
    event: Event
    gender: Gender | None
    grade_from: int
    grade_to: int
    count: int

    @property
    def unit(self) -> str:
        return "팀" if self.event is Event.TEAM else "명"

    @property
    def passes(self) -> int:
        return pass_count(self.count)


@dataclass(frozen=True)
class MergeAdvice:
    """first 와 second 를 합치면 부전승이 before 번에서 after 번으로 준다."""

    first: DivisionSize
    second: DivisionSize

    @property
    def labels(self) -> tuple[str, str]:
        return self.first.label, self.second.label

    @property
    def merged_count(self) -> int:
        return self.first.count + self.second.count

    @property
    def before(self) -> int:
        return self.first.passes + self.second.passes

    @property
    def after(self) -> int:
        return pass_count(self.merged_count)


@dataclass(frozen=True)
class ByeReport:
    """merges 는 합치기 추천, keep 은 부전승이 있지만 합쳐도 줄지 않는 부문."""

    merges: tuple[MergeAdvice, ...] = ()
    keep: tuple[DivisionSize, ...] = ()

    @property
    def has_byes(self) -> bool:
        return bool(self.merges or self.keep)


def _school_level(grade: int) -> int:
    return sum(grade > last for last in (ELEMENTARY_LAST, MIDDLE_LAST, HIGH_LAST))


def _adjacent(a: DivisionSize, b: DivisionSize) -> bool:
    """같은 종목·성별·학교급에서 학년이 바로 이어지는가. 초6 과 중1 처럼 학교급을 넘으면 권하지 않는다."""
    same_kind = a.event is b.event and a.gender is b.gender
    touching = b.grade_from == a.grade_to + 1
    levels = {_school_level(grade) for grade in (a.grade_from, a.grade_to, b.grade_from, b.grade_to)}
    return same_kind and touching and len(levels) == 1


def _candidates(sizes: Sequence[DivisionSize]) -> list[MergeAdvice]:
    occupied = [size for size in sizes if size.count > 0]
    pairs = [MergeAdvice(a, b) for a in occupied for b in occupied if _adjacent(a, b)]
    return [pair for pair in pairs if pair.after < pair.before]


def bye_report(sizes: Sequence[DivisionSize]) -> ByeReport:
    """부전승을 가장 많이 줄이는 짝부터 고르고, 이미 고른 부문이 들어간 짝은 건너뛴다."""
    chosen: list[MergeAdvice] = []
    used: set[str] = set()
    for advice in sorted(_candidates(sizes), key=lambda a: (a.after - a.before, a.after)):
        if used.isdisjoint(advice.labels):
            chosen.append(advice)
            used.update(advice.labels)
    keep = tuple(size for size in sizes if size.count > 1 and size.passes > 0 and size.label not in used)
    return ByeReport(tuple(chosen), keep)
