"""단체전 부문은 신청서에 적힌 팀 종별대로 만든다(운영자: 「서류상 기준으로」).

신청서의 「팀별」 칸(초등저학년 1~3학년 · 여청소년부(중,고) · 남자일반부 …)이 곧 단체전 부문이다.
종별에 성별이 없으면 혼성, 있으면 그 성별이다. 그래서 「혼성으로 할지」「몇 명 팀인지」를 운영자가 따로 고르지 않는다.
"""

from __future__ import annotations

from collections.abc import Sequence

from kendo_tournament.domain.division.category_label import Category, band_name, has_band_word, parse_category
from kendo_tournament.domain.model import ADULT, DivisionRule, Event, Grade, Team


def team_category(team: Team) -> Category | None:
    """팀의 종별을 읽는다. 종별이 없거나(예전 파일·다른 양식) 알아볼 수 없으면 None."""
    return parse_category(team.category) if team.category else None


def _named(label: str, category: Category) -> tuple[Category, str]:
    """나이 없는 성인 종별(「중년부」)은 부 이름으로 나눈다. 안 그러면 청년부·장년부·중년부가 모두 「성인」 하나가 된다."""
    nameless = category.grade_from == ADULT and category.age_from is None and has_band_word(label)
    return category, band_name(label) if nameless else ""


def team_rules(
    teams: Sequence[Team],
    existing_ids: Sequence[str] = (),
    min_entries: int | None = None,
    labels: Sequence[str] = (),
) -> list[DivisionRule]:
    """종별 표의 단체전 종별을 표 순서대로, 그 뒤에 팀 신청서에만 있는 종별을 처음 나온 순서대로. 같은 종별은 한 번만."""
    used = set(existing_ids)
    seen: set[tuple[Category, str]] = set()
    rules = []
    texts = [*labels, *(team.category for team in teams if team.category)]
    for label in texts:
        category = parse_category(label)
        if category is None or _named(label, category) in seen:
            continue
        key = _named(label, category)
        seen.add(key)
        rules.append(
            DivisionRule(
                next_rule_id(used),
                Event.TEAM,
                category.gender,
                Grade(category.grade_from),
                Grade(category.grade_to),
                None,
                min_entries,
                category.age_from,
                category.age_to,
                key[1],
            )
        )
    return rules


def fits_team_rule(team: Team, rule: DivisionRule) -> bool | None:
    """종별이 있는 팀이 이 규칙에 드는가. 성별(혼성은 혼성끼리)이 같고 학년 범위가 규칙 안이어야 한다.

    종별이 없는 팀이면 None — 그때는 팀원 성별·학년으로 판단한다(builder).
    """
    category = team_category(team)
    if category is None:
        return None
    if category.gender is not rule.gender:
        return False
    if rule.age_name and not rule.has_age_band and band_name(team.category) != rule.age_name:
        return False
    return rule.grade_from.value <= category.grade_from and category.grade_to <= rule.grade_to.value


def next_rule_id(used: set[str]) -> str:
    number = len(used) + 1
    while f"r{number}" in used:
        number += 1
    used.add(f"r{number}")
    return f"r{number}"
