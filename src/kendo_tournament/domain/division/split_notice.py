"""신청서가 학년을 묶어 적은 종별(「남초등 1~2학년」)을 규칙이 학년별로 나누려 할 때의 알림.

그런 신청서는 선수마다 학년이 없어 학년별 부문으로 나눌 근거가 없다. 몰래 한쪽 부문에 몰거나 빼지 말고 운영자에게 알린다
(운영자 신고: 「학년 다 나눴는데 왜 묶어서 나옴」).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from kendo_tournament.domain.division.category_label import Category
from kendo_tournament.domain.division.individual_categories import placement_category
from kendo_tournament.domain.model import DivisionRule, Event, Participant


def combined_grade_notices(
    individuals: Sequence[Participant],
    rules: Sequence[DivisionRule],
    chosen: Mapping[str, str],
) -> list[str]:
    """학년이 묶인 종별인데 그 범위를 가르는 학년 규칙이 있으면, 종별·들어간 부문마다 한 줄씩 알린다.

    chosen 은 선수 id → 들어간 규칙 id(narrowest_rule_ids). 없으면 어느 부문에도 안 들어간 것이다.
    """
    by_id = {rule.id: rule for rule in rules}
    counts: dict[tuple[str, str | None], int] = {}
    for person in individuals:
        category = placement_category(person)
        if category is None or not _is_split(category, rules):
            continue
        key = (person.category, chosen.get(person.id))
        counts[key] = counts.get(key, 0) + 1
    return [_notice(label, by_id.get(rule_id) if rule_id else None, count) for (label, rule_id), count in counts.items()]


def _is_split(category: Category, rules: Sequence[DivisionRule]) -> bool:
    if category.grade_from == category.grade_to or category.age_from is not None:
        return False
    return any(_cuts(category, rule) for rule in rules)


def _cuts(category: Category, rule: DivisionRule) -> bool:
    """같은 성별의 학년 규칙이 종별 범위와 겹치지만 다 담지 못한다(예: 1~2학년 종별과 초1 규칙)."""
    if rule.event is not Event.INDIVIDUAL or rule.has_age_band:
        return False
    if rule.gender is not None and rule.gender is not category.gender:
        return False
    overlaps = rule.grade_from.value <= category.grade_to and category.grade_from <= rule.grade_to.value
    contains = rule.grade_from.value <= category.grade_from and category.grade_to <= rule.grade_to.value
    return overlaps and not contains


def _notice(label: str, rule: DivisionRule | None, count: int) -> str:
    head = f"「{label}」 {count}명: 신청서에 학년이 함께 적혀 있어 학년별 종별으로 나눌 수 없습니다."
    if rule is not None:
        return f"{head} 「{rule.label}」에 넣었습니다. 나누려면 명단에서 선수마다 나이를 적어 주세요."
    return f"{head} 들어갈 종별이 없어 빠졌습니다. 이 범위의 기준을 더하거나 명단에서 선수마다 나이를 적어 주세요."
