"""「빠른 설정 → 규칙 추가」: 대회 종별 표대로 부문 규칙을 한꺼번에 만든다. 학교급 이름(쪽 제목용)도 여기 둔다.

예전에는 성별·학교급·학년 묶기·성인 나이를 체크로 골랐다. 대회 종별 표(요강)가 그 일을 하게 되어 칸을 없앴다(운영자 합의).
표에 안 드는 선수·팀은 부문 화면의 「빠진 선수·팀 부문 만들기」가 따로 규칙을 만든다(unplaced).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from kendo_tournament.domain.division.category_table import DEFAULT_CATEGORY_TABLE, CategoryTable
from kendo_tournament.domain.division.individual_categories import individual_entrants, individual_rules
from kendo_tournament.domain.division.team_categories import team_rules
from kendo_tournament.domain.model import (
    ADULT,
    ELEMENTARY_LAST,
    HIGH_LAST,
    MIDDLE_LAST,
    DivisionRule,
    Event,
    Grade,
    Participant,
    Team,
)


class SchoolLevel(Enum):
    ELEMENTARY = ("초등부", 1, ELEMENTARY_LAST)
    MIDDLE = ("중등부", ELEMENTARY_LAST + 1, MIDDLE_LAST)
    HIGH = ("고등부", MIDDLE_LAST + 1, HIGH_LAST)
    ADULT = ("성인부", ADULT, ADULT)

    @property
    def label(self) -> str:
        return self.value[0]

    @property
    def first(self) -> int:
        return self.value[1]

    @property
    def last(self) -> int:
        return self.value[2]


@dataclass(frozen=True)
class PresetChoice:
    """고른 종목과 인원 기준, 그리고 대회 종별 표."""

    events: tuple[Event, ...]
    min_entries: int | None = None
    categories: CategoryTable = DEFAULT_CATEGORY_TABLE


MIDDLE_HIGH_TITLE = "중고등부"


def make_rules(
    choice: PresetChoice,
    existing_ids: Sequence[str] = (),
    teams: Sequence[Team] = (),
    participants: Sequence[Participant] = (),
) -> list[DivisionRule]:
    """고른 종목마다 종별 표의 종별을 규칙으로, 그 뒤에 신청서에만 있는 다른 종별을 더한다. id 는 기존과 겹치지 않는다."""
    used = set(existing_ids)
    rules: list[DivisionRule] = []
    for event in choice.events:
        if event is Event.TEAM:
            made = team_rules(teams, sorted(used), choice.min_entries, choice.categories.team)
        else:
            entrants = individual_entrants(participants, teams)
            made = individual_rules(entrants, sorted(used), choice.min_entries, choice.categories.individual)
        used |= {rule.id for rule in made}
        rules += made
    return rules


def level_title(grade_from: Grade, grade_to: Grade) -> str | None:
    """쪽 제목에 쓸 학교급 이름. 중등·고등에 걸치면 「중고등부」, 아니면 가장 낮은 학년의 학교급."""
    covered = [level for level in SchoolLevel if level.first <= grade_to.value and grade_from.value <= level.last]
    if covered == [SchoolLevel.MIDDLE, SchoolLevel.HIGH]:
        return MIDDLE_HIGH_TITLE
    return covered[0].label if covered else None
