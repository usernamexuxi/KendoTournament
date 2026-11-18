"""어느 부문에도 들지 못한 선수·팀: 왜 빠졌는지 묶어 알리고, 들어갈 부문 규칙을 만들어 해결한다(운영자: 「안 되게 하거나 해결 방법을 추천」).

개인전 선수는 신청서 종별이 있으면 그 종별마다, 없으면 성별·학년(성인은 성인 하나)마다, 단체전 팀은 신청서 종별마다 규칙 하나를 만든다.
성별을 모르는 개인전 선수는 부문을 정할 수 없으므로 명단에서 성별을 채우라고만 알린다.
"""

from __future__ import annotations

from collections.abc import Sequence

from kendo_tournament.domain.division.builder import DivisionResult
from kendo_tournament.domain.division.grade import resolve_grade
from kendo_tournament.domain.division.individual_categories import category_rules, participant_category
from kendo_tournament.domain.division.team_categories import team_rules
from kendo_tournament.domain.model import DivisionRule, Event, Gender, Grade, Participant

NAMES_SHOWN = 6


def _kind(person: Participant) -> tuple[Gender, Grade] | None:
    grade = resolve_grade(person)
    if person.gender is None or grade is None:
        return None
    return person.gender, grade


def _names(names: Sequence[str], unit: str = "명") -> str:
    shown = ", ".join(names[:NAMES_SHOWN])
    return shown + (f" 외 {len(names) - NAMES_SHOWN}{unit}" if len(names) > NAMES_SHOWN else "")


def unplaced_lines(result: DivisionResult) -> list[str]:
    """빠진 선수는 성별·학년마다, 빠진 팀은 한 줄로 이유와 할 일을 적는다."""
    grouped: dict[tuple[Gender, Grade] | None, list[str]] = {}
    by_category: dict[str, list[str]] = {}
    for person in result.unassigned:
        if participant_category(person) is not None:
            by_category.setdefault(person.category, []).append(f"{person.name}({person.dojang})")
        else:
            grouped.setdefault(_kind(person), []).append(f"{person.name}({person.dojang})")
    lines = [
        f"종별 「{label}」 {len(names)}명: {_names(names)} — 이 종별 전체를 담는 개인전 종별이 없습니다(신청서에 학년이 없어 학년별로 못 나눕니다)."
        for label, names in by_category.items()
    ]
    for kind, names in grouped.items():
        if kind is None:
            lines.append(f"성별이나 학년을 몰라 종별을 정할 수 없는 선수 {len(names)}명: {_names(names)} — 명단에서 채워 주세요.")
            continue
        gender, grade = kind
        lines.append(f"{gender.value}자 {grade.label} {len(names)}명: {_names(names)} — 이 학년 개인전 종별이 없습니다.")
    if result.unplaced_teams:
        teams = [team.name for team in result.unplaced_teams]
        lines.append(f"단체전 팀 {len(teams)}개: {_names(teams, '개')} — 들어갈 단체전 종별이 없습니다.")
    return lines


def missing_rules(
    result: DivisionResult, existing_ids: Sequence[str] = (), participants: Sequence[Participant] = ()
) -> list[DivisionRule]:
    """빠진 선수·팀이 들어갈 규칙. 성별·학년을 모르는 선수는 정할 수 없어 뺀다.

    종별 없는 팀(예전 파일)은 팀원으로 정한다: 성별이 모두 같으면 그 성별, 아니면 혼성, 학년은 팀원 범위.
    """
    used = set(existing_ids)
    rules = category_rules(result.unassigned, sorted(used))
    used |= {rule.id for rule in rules}
    plain = [person for person in result.unassigned if participant_category(person) is None]
    kinds = sorted({kind for person in plain if (kind := _kind(person))}, key=lambda k: (k[0].name, k[1].value))
    for gender, grade in kinds:
        rule_id = _next_id(used)
        rules.append(DivisionRule(rule_id, Event.INDIVIDUAL, gender, grade, grade))
    with_category = [team for team in result.unplaced_teams if team.category]
    from_teams = team_rules(with_category, sorted(used))
    used |= {rule.id for rule in from_teams}
    people = {person.id: person for person in participants}
    from_members: dict[tuple, DivisionRule] = {}
    for team in result.unplaced_teams:
        members = [people[m] for m in team.member_ids if m in people]
        grades = [g for g in (resolve_grade(m) for m in members) if g is not None]
        if team.category or not grades:
            continue
        genders = {m.gender for m in members}
        gender = genders.pop() if len(genders) == 1 else None
        key = (gender, min(grades).value, max(grades).value)
        if key not in from_members:
            low, high = min(grades), max(grades)
            from_members[key] = DivisionRule(_next_id(used), Event.TEAM, gender, low, high)
    return rules + from_teams + list(from_members.values())


def _next_id(used: set[str]) -> str:
    number = len(used) + 1
    while f"r{number}" in used:
        number += 1
    used.add(f"r{number}")
    return f"r{number}"
