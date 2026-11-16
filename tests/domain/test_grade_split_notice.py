"""신청서가 학년을 「1~2학년」처럼 묶어 적었는데 규칙은 학년마다 나눈 경우(운영자 신고: 「학년 다 나눴는데 왜 묶어서 나옴」).

운영자 지시: 학년이 따로 적혀 온 선수만 학년별로 나눈다. 묶여 온 것을 나누려 하면 알린다. 나이를 알면 나이로 학년을 정한다.
"""

from kendo_tournament.domain.division.builder import build_divisions
from kendo_tournament.domain.model import DivisionRule, Event, Gender, Grade, Participant


def per_grade_rules(*extra):
    rules = [DivisionRule(f"g{g}", Event.INDIVIDUAL, Gender.MALE, Grade(g), Grade(g)) for g in range(1, 7)]
    return rules + list(extra)


def kid(pid, category, age=None, grade=1):
    return Participant(pid, f"선수{pid}", Gender.MALE, "도장", Grade(grade), age, category=category)


def test_학년이_따로_적혀_온_선수는_학년별_부문으로_나뉜다():
    people = [
        kid("a", "남초등 1학년"),
        kid("d", "남초등 1학년"),
        kid("b", "남초등 2학년", grade=2),
        kid("c", "남초등 2학년", grade=2),
    ]
    result = build_divisions(people, [], per_grade_rules())
    assert sorted((d.label, len(d.entries)) for d in result.divisions) == [("남자 초1 개인전", 2), ("남자 초2 개인전", 2)]
    assert not any("함께 적혀" in w for w in result.warnings)


def test_묶여_온_종별을_학년별로_나누려_하면_알린다():
    people = [kid(str(i), "남초등 1~2학년") for i in range(4)]
    result = build_divisions(people, [], per_grade_rules())
    notice = [w for w in result.warnings if "함께 적혀" in w]
    assert notice and "1~2학년" in notice[0] and "4명" in notice[0]


def test_묶여_온_종별에_맞는_넓은_부문이_있으면_그리로_가고_그래도_알린다():
    wide = DivisionRule("w", Event.INDIVIDUAL, Gender.MALE, Grade(1), Grade(2))
    people = [kid(str(i), "남초등 1~2학년") for i in range(4)]
    result = build_divisions(people, [], per_grade_rules(wide))
    assert [(d.label, len(d.entries)) for d in result.divisions] == [("남자 초1~초2 개인전", 4)]
    notice = [w for w in result.warnings if "함께 적혀" in w]
    assert notice and "남자 초1~초2 개인전" in notice[0]


def test_나이를_알면_묶여_온_종별도_나이로_학년을_정해_나눈다():
    ages = {"a": 8, "d": 8, "b": 9, "c": 9}
    people = [kid(pid, "남초등 1~2학년", age=age) for pid, age in ages.items()]
    result = build_divisions(people, [], per_grade_rules())
    entries = {d.label: sorted(e.id for e in d.entries) for d in result.divisions}
    assert entries == {"남자 초1 개인전": ["a", "d"], "남자 초2 개인전": ["b", "c"]}
    assert not any("함께 적혀" in w for w in result.warnings)


def test_나이가_종별_범위_밖이면_나이를_믿지_않고_종별대로_둔다():
    wide = DivisionRule("w", Event.INDIVIDUAL, Gender.MALE, Grade(1), Grade(2))
    people = [kid("a", "남초등 1~2학년", age=12), kid("b", "남초등 1~2학년")]
    result = build_divisions(people, [], per_grade_rules(wide))
    assert [(d.label, len(d.entries)) for d in result.divisions] == [("남자 초1~초2 개인전", 2)]
