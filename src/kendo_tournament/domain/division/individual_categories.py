"""개인전 부문도 신청서에 적힌 종별대로 만든다(운영자: 「홍성수관.hwp 2쪽 개인전 종별이 기본 기준」).

개인전 신청서는 「남초등 1~2학년」 줄에 이름만 늘어놓아 선수마다 학년이 없다. 리더는 학년을 범위의 첫 값으로 채우므로,
학년마다 부문을 나누면 1~2학년 선수가 모두 초1 부문에 몰리고 초2 부문은 늘 빈다. 그래서 종별 범위가 곧 부문이다.
"""

from __future__ import annotations

from collections.abc import Sequence

from kendo_tournament.domain.division.category_label import Category, band_name, fill_missing_gender, parse_category
from kendo_tournament.domain.division.category_table import DEFAULT_CATEGORY_TABLE
from kendo_tournament.domain.division.grade import grade_from_age
from kendo_tournament.domain.division.team_categories import next_rule_id
from kendo_tournament.domain.model import (
    ELEMENTARY_LAST,
    HIGH_LAST,
    MIDDLE_LAST,
    DivisionRule,
    Event,
    Gender,
    Grade,
    Participant,
    Team,
)

OPEN_AGE = 200


def participant_category(person: Participant) -> Category | None:
    """선수의 개인전 종별. 성별은 선수 것을 쓴다 — 「중등부」처럼 종별에 성별이 없을 때 리더가 채워 둔 값이다."""
    category = parse_category(person.category) if person.category else None
    if category is None:
        return None
    return Category(person.gender, category.grade_from, category.grade_to, category.age_from, category.age_to)


def placement_category(person: Participant) -> Category | None:
    """부문에 넣을 때 쓰는 종별. 「1~2학년」처럼 묶인 종별이라도 나이를 알고 그 나이의 학년이 범위 안이면 그 학년 하나로 좁힌다.

    운영자 지시: 나이를 알 수 있으면 나이로 학년을 정해 나눈다. 범위 밖 나이는 잘못 적힌 것으로 보고 종별을 따른다.
    """
    category = participant_category(person)
    if category is None or category.grade_from == category.grade_to or person.age is None:
        return category
    grade = grade_from_age(person.age)
    if grade is None or not category.grade_from <= grade.value <= category.grade_to:
        return category
    return Category(category.gender, grade.value, grade.value, category.age_from, category.age_to)


def individual_entrants(participants: Sequence[Participant], teams: Sequence[Team]) -> list[Participant]:
    """단체전 팀원을 뺀 선수. 팀원은 팀으로 나가므로 개인전 부문을 만들 근거가 아니다."""
    members = {member for team in teams for member in team.member_ids}
    return [person for person in participants if person.id not in members]


def _table_categories(labels: Sequence[str]) -> list[tuple[Category, str]]:
    """종별 표의 글을 읽는다. 「중등부」처럼 성별 없는 글은 같은 학년대의 반대 성별 종별로 채운다(요강 모양)."""
    readable = [label for label in labels if parse_category(label) is not None]
    parsed = [category for label in readable if (category := parse_category(label)) is not None]
    return list(zip(fill_missing_gender(parsed), readable, strict=True))


def individual_rules(
    participants: Sequence[Participant],
    existing_ids: Sequence[str] = (),
    min_entries: int | None = None,
    labels: Sequence[str] = DEFAULT_CATEGORY_TABLE.individual,
) -> list[DivisionRule]:
    """대회 종별 표의 개인전 종별을 표 순서대로, 그 뒤에 선수들 신청서에만 있는 다른 종별을 하나씩 더한다.

    선수가 없는 종별도 규칙은 만든다 — 빈 부문은 대진표에 안 나온다. 다른 양식의 종별은 학교급 → 남자 먼저 → 학년 순이다.
    """
    used = set(existing_ids)
    defaults = [_rule(next_rule_id(used), category, label, min_entries) for category, label in _table_categories(labels)]
    # 기본 부문 안에 드는 종별(예전 양식의 「청년부 20~29세」는 청년부 20~35세 안)은 따로 만들지 않는다. 만들면 두 부문에 든다.
    extra = [(c, label) for c, label in _categories_of(participants) if not any(category_fits(c, r) for r in defaults)]
    return defaults + [_rule(next_rule_id(used), category, label, min_entries) for category, label in extra]


def category_rules(participants: Sequence[Participant], existing_ids: Sequence[str] = ()) -> list[DivisionRule]:
    """이 선수들의 종별만 규칙으로(종별 표 없이). 부문에서 빠진 종별 선수를 되살릴 때 쓴다."""
    used = set(existing_ids)
    return [_rule(next_rule_id(used), category, label, None) for category, label in _categories_of(participants)]


def _categories_of(participants: Sequence[Participant]) -> list[tuple[Category, str]]:
    found: dict[Category, str] = {}
    for person in participants:
        category = participant_category(person)
        if category is not None and category not in found:
            found[category] = person.category
    return sorted(found.items(), key=lambda item: _form_order(item[0]))


def _rule(rule_id: str, category: Category, label: str, min_entries: int | None) -> DivisionRule:
    return DivisionRule(
        rule_id,
        Event.INDIVIDUAL,
        category.gender,
        Grade(category.grade_from),
        Grade(category.grade_to),
        None,
        min_entries,
        category.age_from,
        category.age_to,
        band_name(label) if category.age_from is not None else "",
    )


def fits_individual_rule(person: Participant, rule: DivisionRule) -> bool | None:
    """종별이 있는 선수가 이 규칙에 드는가. 종별 범위 전체가 규칙 안이어야 한다(1~2학년 선수는 초1 단독 부문에 안 든다).

    종별이 없는 선수면 None — 그때는 학년·나이로 판단한다(builder).
    """
    category = placement_category(person)
    return None if category is None else category_fits(category, rule)


def narrowest_rule_ids(participants: Sequence[Participant], rules: Sequence[DivisionRule]) -> dict[str, str]:
    """종별 선수마다 들어갈 개인전 규칙 하나. 여러 규칙에 들면 범위가 가장 좁은 규칙이다.

    양식마다 나이 구간이 달라 「중년부 48세부터」 선수가 「중년부 40세부터」 규칙에도 든다. 좁은 쪽이 신청서 뜻에 가깝다.
    """
    individual = [rule for rule in rules if rule.event is Event.INDIVIDUAL]
    chosen = {}
    for person in participants:
        category = placement_category(person)
        fitting = [rule for rule in individual if category is not None and category_fits(category, rule)]
        if fitting:
            chosen[person.id] = min(fitting, key=_width).id
    return chosen


def _width(rule: DivisionRule) -> tuple[int, int]:
    ages = (rule.age_to or OPEN_AGE) - (rule.age_from or 0) if rule.has_age_band else OPEN_AGE
    return rule.grade_to.value - rule.grade_from.value, ages


def category_fits(category: Category, rule: DivisionRule) -> bool:
    """종별의 성별이 같고, 학년 범위와 나이 범위가 모두 규칙 안에 드는가."""
    if rule.gender is not None and category.gender is not rule.gender:
        return False
    if not rule.grade_from.value <= category.grade_from or not category.grade_to <= rule.grade_to.value:
        return False
    return _ages_inside(category, rule)


def _ages_inside(category: Category, rule: DivisionRule) -> bool:
    """「30~39세」 종별은 「20~35세」 규칙에 안 든다 — 36~39세일 수 있다. 신청서가 나이를 범위로만 적기 때문이다."""
    if not rule.has_age_band:
        return True
    if category.age_from is None or rule.age_from is None or category.age_from < rule.age_from:
        return False
    if rule.age_to is None:
        return True
    return category.age_to is not None and category.age_to <= rule.age_to


def _form_order(category: Category) -> tuple[int, int, int, int]:
    level = sum(category.grade_from > last for last in (ELEMENTARY_LAST, MIDDLE_LAST, HIGH_LAST))
    gender = 0 if category.gender is Gender.MALE else 1
    return level, gender, category.grade_from, category.age_from or 0
