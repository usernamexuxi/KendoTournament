"""나뉜 부문을 운영자가 손으로 고친다: 여러 부문을 하나로 합치기, 합쳐진 부문을 학년별로 나누기.

고친 결과는 규칙으로 남긴다. 그래야 명단이 바뀌어 부문을 다시 나눠도 고친 것이 유지된다.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from kendo_tournament.domain.model import DivisionRule, Grade


def _picked(rules: Sequence[DivisionRule], rule_ids: Sequence[str]) -> list[DivisionRule]:
    wanted = set(rule_ids)
    picked = [rule for rule in rules if rule.id in wanted]
    if len(picked) != len(wanted):
        raise ValueError("고르신 부문의 규칙을 찾지 못했습니다. 「부문 나누기」를 다시 눌러 주세요.")
    return picked


def merge_rules(rules: Sequence[DivisionRule], rule_ids: Sequence[str]) -> list[DivisionRule]:
    """고른 규칙들을 학년 범위가 이어진 규칙 하나로 바꾼다. 첫 규칙 자리에 들어간다.

    종목·성별이 다르거나, 고른 규칙들 사이에 학년이 비면 ValueError.
    예: 초1 규칙과 초3 규칙만 고르고 초2 규칙은 안 고른 경우.
    """
    picked = sorted(_picked(rules, rule_ids), key=lambda rule: rule.grade_from.value)
    if len(picked) < 2:
        raise ValueError("합칠 부문을 둘 이상 골라 주세요.")
    head = picked[0]
    if any(rule.event is not head.event or rule.gender is not head.gender for rule in picked):
        raise ValueError("종목과 성별이 같은 부문끼리만 합칠 수 있습니다.")
    for lower, upper in zip(picked, picked[1:], strict=False):
        if upper.grade_from.value != lower.grade_to.value + 1:
            raise ValueError("학년이 이어지는 부문끼리만 합칠 수 있습니다. 사이에 낀 부문도 함께 골라 주세요.")
    merged = replace(head, grade_to=picked[-1].grade_to)
    removed = {rule.id for rule in picked}
    first_position = min(index for index, rule in enumerate(rules) if rule.id in removed)
    result = [rule for rule in rules if rule.id not in removed]
    result.insert(first_position, merged)
    return result


def split_rules(rules: Sequence[DivisionRule], rule_ids: Sequence[str]) -> list[DivisionRule]:
    """고른 규칙들을 한 학년짜리 규칙으로 쪼개고 인원 기준을 없앤다(기준 때문에 다시 합쳐지지 않게).

    혼자인 학년은 부문을 다시 나눌 때 옆 학년과 또 합쳐진다.
    """
    wanted = {rule.id for rule in _picked(rules, rule_ids)}
    used = {rule.id for rule in rules}
    result: list[DivisionRule] = []
    for rule in rules:
        if rule.id not in wanted:
            result.append(rule)
            continue
        for value in range(rule.grade_from.value, rule.grade_to.value + 1):
            rule_id = rule.id if value == rule.grade_from.value else _fresh_id(f"{rule.id}-{value}", used)
            result.append(replace(rule, id=rule_id, grade_from=Grade(value), grade_to=Grade(value), min_entries=None))
    return result


def _fresh_id(wanted: str, used: set[str]) -> str:
    candidate, number = wanted, 2
    while candidate in used:
        candidate, number = f"{wanted}-{number}", number + 1
    used.add(candidate)
    return candidate
