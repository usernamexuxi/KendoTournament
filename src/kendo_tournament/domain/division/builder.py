"""운영자가 정한 부문 규칙으로 명단을 부문별로 나눈다."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

from kendo_tournament.domain.division.bye_notice import ByeReport, DivisionSize, bye_report
from kendo_tournament.domain.division.grade import resolve_grade
from kendo_tournament.domain.division.individual_categories import (
    fits_individual_rule,
    narrowest_rule_ids,
    participant_category,
)
from kendo_tournament.domain.division.split_notice import combined_grade_notices
from kendo_tournament.domain.division.team_categories import fits_team_rule
from kendo_tournament.domain.model import (
    ELEMENTARY_LAST,
    HIGH_LAST,
    MIDDLE_LAST,
    Division,
    DivisionRule,
    Entry,
    Event,
    Grade,
    Participant,
    Team,
)


@dataclass(frozen=True)
class DivisionResult:
    divisions: tuple[Division, ...]
    unassigned: tuple[Participant, ...]
    multi_assigned: tuple[Participant, ...]
    warnings: tuple[str, ...]
    byes: ByeReport = ByeReport()
    unplaced_teams: tuple[Team, ...] = ()


@dataclass(frozen=True)
class _Group:
    rules: tuple[DivisionRule, ...]
    grade_from: Grade
    grade_to: Grade
    entries: tuple[Entry, ...]

    @property
    def head(self) -> DivisionRule:
        return self.rules[0]

    @property
    def label(self) -> str:
        return replace(self.head, grade_from=self.grade_from, grade_to=self.grade_to).label


def _in_range(grade: Grade | None, rule: DivisionRule) -> bool:
    return grade is not None and rule.grade_from <= grade <= rule.grade_to


def matches_individual(person: Participant, rule: DivisionRule) -> bool:
    """개인전 규칙에 드는가. 종별이 있는 선수는 종별 범위로, 없으면 성별·나이·학년으로."""
    by_category = fits_individual_rule(person, rule)
    if by_category is not None:
        return by_category
    return _matches_by_grade(person, rule)


def _matches_by_grade(person: Participant, rule: DivisionRule) -> bool:
    if rule.gender is not None and person.gender is not rule.gender:
        return False
    if not rule.age_fits(person.age):
        return False
    return _in_range(resolve_grade(person), rule)


def _matches_team(team: Team, people: dict[str, Participant], rule: DivisionRule) -> bool:
    """종별이 있는 팀은 종별로(혼성 팀은 혼성 부문에만), 없는 팀은 팀원 성별·학년으로 판단한다."""
    members = [people.get(member_id) for member_id in team.member_ids]
    if not members or any(member is None for member in members):
        return False
    by_category = fits_team_rule(team, rule)
    if by_category is not None:
        return by_category
    return all(matches_individual(member, rule) for member in members if member)


@dataclass(frozen=True)
class _Roster:
    """individuals 는 개인전에 나갈 선수, chosen 은 종별 선수마다 들어갈 규칙 하나(가장 좁은 범위)."""

    participants: tuple[Participant, ...]
    individuals: tuple[Participant, ...]
    teams: tuple[Team, ...]
    chosen: dict[str, str]


def _roster(participants: Sequence[Participant], teams: Sequence[Team], rules: Sequence[DivisionRule]) -> _Roster:
    # 종별 있는 팀은 종별 신청서의 단체전 표에서만 나온다. 그 팀원은 개인전 표에 이름이 없으면 개인전 신청자가 아니다.
    form_members = {member for team in teams if team.category for member in team.member_ids}
    individuals = tuple(p for p in participants if p.id not in form_members)
    return _Roster(tuple(participants), individuals, tuple(teams), narrowest_rule_ids(individuals, rules))


def _individual_fits(person: Participant, rule: DivisionRule, roster: _Roster) -> bool:
    if participant_category(person) is not None:
        return roster.chosen.get(person.id) == rule.id
    return _matches_by_grade(person, rule)


def _entries_for(rule: DivisionRule, roster: _Roster) -> tuple[Entry, ...]:
    if rule.event is Event.INDIVIDUAL:
        return tuple(Entry(p.id, p.name, p.dojang) for p in roster.individuals if _individual_fits(p, rule, roster))
    people = {p.id: p for p in roster.participants}
    return tuple(Entry(t.id, team_display_name(t), t.dojang, team=True) for t in roster.teams if _matches_team(t, people, rule))


def team_display_name(team: Team) -> str:
    """대진표 칸에 쓸 팀 이름. 칸은 「(도장) 이름」이라, 신청서에서 읽은 「도장 팀」의 앞 도장을 뗀다."""
    short = team.name.removeprefix(f"{team.dojang} ").strip()
    return short or team.name


def _same_kind(a: _Group, b: _Group) -> bool:
    """같은 종목·성별. 나이 구간 부문(청년부 20~35세)은 학년 부문과 합치지 않는다 — 학년이 모두 성인이라 고3 과 이웃으로 보여
    성인 한 명이 고등부에 섞이고 부문 이름은 나이 구간으로 남았다."""
    if a is b or a.head.event is not b.head.event or a.head.gender is not b.head.gender:
        return False
    return not a.head.has_age_band and not b.head.has_age_band


def _upper_neighbor(groups: list[_Group], group: _Group) -> _Group | None:
    return next((o for o in groups if _same_kind(o, group) and o.grade_from.value == group.grade_to.value + 1), None)


def _lower_neighbor(groups: list[_Group], group: _Group) -> _Group | None:
    return next((o for o in groups if _same_kind(o, group) and o.grade_to.value == group.grade_from.value - 1), None)


def _merge(lower: _Group, upper: _Group, first: _Group) -> _Group:
    seen: set[str] = set()
    entries = []
    for entry in lower.entries + upper.entries:
        if entry.id not in seen:
            seen.add(entry.id)
            entries.append(entry)
    rules = first.rules + (upper.rules if first is lower else lower.rules)
    return _Group(rules, lower.grade_from, upper.grade_to, tuple(entries))


SOLO = 1


def _is_short(group: _Group) -> bool:
    minimum = group.head.min_entries
    return len(group.entries) == SOLO or bool(minimum and len(group.entries) < minimum)


def _school_level(grade: Grade) -> int:
    return sum(grade.value > last for last in (ELEMENTARY_LAST, MIDDLE_LAST, HIGH_LAST))


def _merge_pair(groups: list[_Group], group: _Group) -> tuple[_Group, _Group] | None:
    """모자란 부문과 합칠 이웃을 (아래 학년, 위 학년) 순으로 고른다.

    학교급이 같은 이웃이 먼저다(고3 을 성인과 묶지 않게). 그다음은 인원이 적은 쪽이라 부문 크기가 고르게 된다.
    둘 다 같으면 위 학년과 합친다.
    """
    upper, lower = _upper_neighbor(groups, group), _lower_neighbor(groups, group)
    options = []
    if upper is not None:
        crosses = _school_level(upper.grade_from) != _school_level(group.grade_to)
        options.append((crosses, len(upper.entries), 0, (group, upper)))
    if lower is not None:
        crosses = _school_level(lower.grade_to) != _school_level(group.grade_from)
        options.append((crosses, len(lower.entries), 1, (lower, group)))
    if not options:
        return None
    return min(options, key=lambda option: option[:3])[3]


def _shortage_warning(group: _Group) -> str:
    if len(group.entries) == SOLO:
        return f"{group.label}: 혼자라 경기가 안 되지만 합칠 부문이 없습니다(같은 종목·성별에 바로 이어지는 학년 부문 없음)."
    return f"{group.label}: {len(group.entries)}명(팀)으로 기준 미달이지만 합칠 부문이 없습니다."


def _merge_small_groups(groups: list[_Group]) -> tuple[list[_Group], list[str]]:
    warnings: list[str] = []
    stuck: set[int] = set()
    while True:
        group = next((g for g in groups if id(g) not in stuck and _is_short(g)), None)
        if group is None:
            return groups, warnings
        if group.head.event is Event.TEAM and len(group.entries) == SOLO:
            # 운영자: 단체전은 미리 말을 맞추고 나와 보통 상대가 있다. 혼자면 다른 종별 팀과 붙이지 말고 경기 없음을 알린다.
            warnings.append(f"{group.label}: 1팀뿐이라 경기가 없습니다. 다른 부문과 합치지 않았습니다.")
            stuck.add(id(group))
            continue
        # 사람이 있는 같은 종목·성별 부문이 따로 없으면 빈 부문만 끌어모아 범위만 넓어진다(초1~성인 1명). 합치지 않는다.
        has_company = any(_same_kind(other, group) and other.entries for other in groups)
        pair = _merge_pair(groups, group) if has_company else None
        if pair is None:
            warnings.append(_shortage_warning(group))
            stuck.add(id(group))
            continue
        lower, upper = pair
        merged = _merge(lower, upper, group)
        index = min(groups.index(lower), groups.index(upper))
        groups = [g for g in groups if g is not lower and g is not upper]
        groups.insert(index, merged)


def build_divisions(
    participants: Sequence[Participant],
    teams: Sequence[Team],
    rules: Sequence[DivisionRule],
) -> DivisionResult:
    """규칙마다 해당 선수(팀)를 모으고, 인원이 모자란 부문은 이웃 부문과 합친다.

    합치기는 같은 종목·같은 성별 안에서 구분 범위가 바로 이어지는 부문과만 하며,
    합친 뒤에도 모자라면 다시 합친다. 혼자인 부문은 인원 기준이 없어도 합친다.
    """
    roster = _roster(participants, teams, rules)
    groups = [_Group((rule,), rule.grade_from, rule.grade_to, _entries_for(rule, roster)) for rule in rules]
    groups, warnings = _merge_small_groups(groups)
    warnings = combined_grade_notices(roster.individuals, rules, roster.chosen) + warnings

    individual_counts: dict[str, int] = {}
    for group in groups:
        if group.head.event is Event.INDIVIDUAL:
            for entry in group.entries:
                individual_counts[entry.id] = individual_counts.get(entry.id, 0) + 1

    placed_teams = {entry.id for group in groups if group.head.event is Event.TEAM for entry in group.entries}
    # 단체전 팀원은 팀으로 단체전에 나간다. 개인전 부문이 없어도 빠진 선수가 아니다(빠진 팀은 따로 센다).
    team_members = {member for team in teams for member in team.member_ids}
    divisions = tuple(Division(tuple(r.id for r in g.rules), g.label, g.head.event, g.entries) for g in groups if g.entries)
    unassigned = tuple(p for p in participants if individual_counts.get(p.id, 0) == 0 and p.id not in team_members)
    unplaced = tuple(team for team in teams if team.id not in placed_teams)
    multi = tuple(p for p in participants if individual_counts.get(p.id, 0) > 1)
    sizes = [
        DivisionSize(g.label, g.head.event, g.head.gender, g.grade_from.value, g.grade_to.value, len(g.entries)) for g in groups
    ]
    return DivisionResult(divisions, unassigned, multi, tuple(warnings), bye_report(sizes), unplaced)
