from dataclasses import replace

from kendo_tournament.domain.division.editing import merge_rules, split_rules
from kendo_tournament.domain.division.individual_categories import individual_rules
from kendo_tournament.domain.model import DivisionRule, Event, Gender, Grade


def _named_rules() -> list[DivisionRule]:
    return individual_rules([], (), None, ("남초등 저학년부", "남초등 고학년부"))


def test_요강_이름이_있는_종별은_제목이_요강_이름이다():
    assert [rule.label for rule in _named_rules()] == ["남자 초등 저학년부 개인전", "남자 초등 고학년부 개인전"]


def test_합치거나_쪼개서_학년_범위가_바뀌면_요강_이름을_떼고_학년으로_부른다():
    rules = _named_rules()
    (merged,) = merge_rules(rules, [rule.id for rule in rules])
    assert merged.label == "남자 초1~초6 개인전"
    split = split_rules(rules[:1], [rules[0].id])
    assert [rule.label for rule in split] == ["남자 초1 개인전", "남자 초2 개인전", "남자 초3 개인전"]


def test_범위가_그대로면_요강_이름이_남는다():
    rule = DivisionRule("r", Event.INDIVIDUAL, Gender.MALE, Grade(1), Grade(3), name="초등 저학년부")
    assert rule.with_grades(Grade(1), Grade(3)).label == "남자 초등 저학년부 개인전"
    assert replace(rule, name="").label == "남자 초1~초3 개인전"
