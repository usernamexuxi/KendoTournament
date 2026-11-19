"""인쇄 순서와 쪽 묶음 제목(「초등부 남자」)을 정해 책자 쪽을 만든다.

기본 순서는 종목(개인전 먼저, 단체전은 맨 뒤 — 운영자 지시) → 학교급 → 성별 → 학년 → 나이다.
성별은 학교급 안에서 남자 먼저다(운영자: 「남자 먼저 하고 여자, 초등부·중등부·고등부·중고등부는 지키고」).
운영자가 확인 화면에서 순서를 바꾸거나
「이 부문부터 새 쪽」을 정하면 대회(print_order · page_breaks)에 남는다.
"""

from __future__ import annotations

from collections.abc import Sequence

from kendo_tournament.application.team_roster import team_member_lines
from kendo_tournament.domain.division.presets import SchoolLevel, level_title
from kendo_tournament.domain.draw.bracket import Bracket
from kendo_tournament.domain.draw.numbering import NumberedBracket, number_matches
from kendo_tournament.domain.layout.booklet import BookletItem, layout_booklet, page_numbers
from kendo_tournament.domain.layout.bracket_layout import leaves_of
from kendo_tournament.domain.layout.primitives import PageLayout
from kendo_tournament.domain.model import Division, DivisionRule, Event, Gender, Grade
from kendo_tournament.domain.tournament import Tournament

GENDER_ORDER = (Gender.MALE, Gender.FEMALE, None)
EVENT_ORDER = (Event.INDIVIDUAL, Event.TEAM)


MIN_ENTRIES_FOR_MATCH = 2


def _rules_of(tournament: Tournament, division: Division) -> list[DivisionRule]:
    return [rule for rule in tournament.rules if rule.id in division.rule_ids]


def _lowest_grade(rules: list[DivisionRule]) -> Grade | None:
    return min((rule.grade_from for rule in rules), default=None, key=lambda grade: grade.value)


def _level(grade: Grade | None) -> SchoolLevel | None:
    if grade is None:
        return None
    return next((level for level in SchoolLevel if level.first <= grade.value <= level.last), None)


def section_title(tournament: Tournament, division: Division) -> str:
    """「초등부 남자」, 「중고등부 여자 단체전」 처럼 쪽 맨 위에 쓸 제목.

    학교급은 부문의 가장 낮은 학년으로 정하되, 중등·고등에 걸친 부문은 「중고등부」다.
    """
    rules = _rules_of(tournament, division)
    lowest = _lowest_grade(rules)
    highest = max((rule.grade_to for rule in rules), default=None, key=lambda grade: grade.value)
    level = level_title(lowest, highest) if lowest is not None and highest is not None else None
    gender = rules[0].gender if rules else None
    parts = [level or "", f"{gender.value}자" if gender else "혼성"]
    if division.event is Event.TEAM:
        parts.append(Event.TEAM.value)
    return " ".join(part for part in parts if part)


def _default_key(tournament: Tournament, division: Division) -> tuple[int, int, int, int, int]:
    rules = _rules_of(tournament, division)
    grade = _lowest_grade(rules)
    level = _level(grade)
    gender = rules[0].gender if rules else None
    youngest = min((rule.age_from or 0 for rule in rules), default=0)
    return (
        EVENT_ORDER.index(division.event),
        list(SchoolLevel).index(level) if level else len(SchoolLevel),
        GENDER_ORDER.index(gender),
        grade.value if grade else 0,
        youngest,
    )


def print_order(tournament: Tournament) -> list[str]:
    """지금 부문들의 인쇄 순서. 운영자가 정한 순서를 앞에 두고, 새로 생긴 부문은 기본 순서로 뒤에 붙인다.

    한 명(한 팀)뿐인 부문은 경기가 없어 빠진다(운영자: 「단독 출전이라는 건 없다, 빼는 거다」).
    """
    playable = [division for division in tournament.divisions if len(division.entries) >= MIN_ENTRIES_FOR_MATCH]
    by_label = {division.label: division for division in playable}
    chosen = [label for label in tournament.print_order if label in by_label]
    rest = [d for d in playable if d.label not in chosen]
    rest.sort(key=lambda division: _default_key(tournament, division))
    return chosen + [division.label for division in rest]


def move_in_order(tournament: Tournament, label: str, step: int) -> None:
    """인쇄 순서에서 부문 하나를 step 칸 옮긴다(위 -1, 아래 +1). 끝을 넘으면 그대로 둔다."""
    order = print_order(tournament)
    index = order.index(label)
    target = index + step
    if 0 <= target < len(order):
        order[index], order[target] = order[target], order[index]
    tournament.print_order = order


def set_print_order(tournament: Tournament, labels: Sequence[str]) -> None:
    """운영자가 목록에서 끌어 옮겨 정한 순서를 그대로 남긴다. 목록에 없는 부문은 기본 순서로 뒤에 붙는다."""
    tournament.print_order = list(labels)


def reset_print_order(tournament: Tournament) -> None:
    """운영자가 바꾼 순서를 버리고 기본 순서로 되돌린다."""
    tournament.print_order = []


def toggle_page_break(tournament: Tournament, label: str) -> None:
    if label in tournament.page_breaks:
        tournament.page_breaks.remove(label)
    else:
        tournament.page_breaks.append(label)


def _booklet_items(tournament: Tournament, labels: Sequence[str]) -> list[tuple[str, BookletItem]]:
    wanted = set(labels)
    divisions = {division.label: division for division in tournament.divisions}
    items = []
    for label in print_order(tournament):
        if label not in wanted:
            continue
        bracket = tournament.brackets.get(label)
        if bracket is None:
            raise KeyError(f"{label} 종별은 아직 대진을 짜지 않았습니다.")
        numbered = number_matches(bracket)
        section = section_title(tournament, divisions[label])
        members = team_member_lines(tournament, bracket) if tournament.book.team_members else {}
        event = divisions[label].event
        numbers = _entry_numbers(bracket, numbered)
        item = BookletItem(
            section,
            bracket,
            numbered,
            label in tournament.page_breaks,
            members=members,
            is_team=event is Event.TEAM,
            numbers=numbers,
        )
        items.append((label, item))
    return items


def _entry_numbers(bracket: Bracket, numbered: NumberedBracket) -> dict[str, int]:
    """칸 id → 출전 번호. 대진표에 그려지는 순서(왼쪽 위→아래, 이어서 오른쪽 위→아래)로 1부터 매긴다.

    운영자: 「경기(종별)마다 1부터 다시」 — 여자 초등 1~3학년부가 끝나면 다음 종별은 다시 1번이다.
    빈 칸(부전승 자리)은 세지 않는다.
    """
    if numbered.root is None:
        return {}
    entries = [bracket.slots[leaf.slot] for leaf in leaves_of(numbered.root)]
    present = [entry for entry in entries if entry is not None]
    return {entry.id: index for index, entry in enumerate(present, start=1)}


def booklet_pages(tournament: Tournament, labels: Sequence[str], first_page: int = 1) -> list[PageLayout]:
    """고른 부문을 인쇄 순서대로 책자 쪽에 싣는다. 대진을 아직 안 짠 부문은 KeyError."""
    return layout_booklet([item for _, item in _booklet_items(tournament, labels)], first_page)


def booklet_page_numbers(tournament: Tournament, labels: Sequence[str]) -> dict[str, int]:
    """고른 부문마다 책자의 몇 쪽에 실리는지. 확인 화면이 목록에 「1쪽」처럼 보여 준다. 안 실리는 부문은 빠진다."""
    labelled = _booklet_items(tournament, labels)
    numbers = page_numbers([item for _, item in labelled])
    return {label: number for (label, _), number in zip(labelled, numbers, strict=True) if number is not None}
