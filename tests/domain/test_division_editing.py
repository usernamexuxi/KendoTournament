import pytest

from kendo_tournament.domain.division.builder import build_divisions
from kendo_tournament.domain.division.editing import merge_rules, split_rules
from kendo_tournament.domain.model import DivisionRule, Event, Gender, Grade, Participant


def rule(rid, gender, start, end, min_entries=None):
    return DivisionRule(rid, Event.INDIVIDUAL, gender, Grade(start), Grade(end), None, min_entries)


def people(gender, *grades):
    return [Participant(f"{gender.name}{i}", f"선수{i}", gender, "가관", grade=Grade(g)) for i, g in enumerate(grades)]


def test_이어진_학년_부문을_하나로_합친다():
    rules = [rule("a", Gender.MALE, 1, 1), rule("b", Gender.MALE, 2, 3), rule("c", Gender.MALE, 4, 4)]
    merged = merge_rules(rules, ["b", "a"])
    assert [(r.id, r.grade_from.value, r.grade_to.value) for r in merged] == [("a", 1, 3), ("c", 4, 4)]


def test_사이가_빈_부문은_합치지_않는다():
    rules = [rule("a", Gender.MALE, 1, 1), rule("b", Gender.MALE, 2, 2), rule("c", Gender.MALE, 3, 3)]
    with pytest.raises(ValueError, match="이어지는"):
        merge_rules(rules, ["a", "c"])


def test_성별이_다른_부문은_합치지_않는다():
    rules = [rule("a", Gender.MALE, 1, 1), rule("b", Gender.FEMALE, 2, 2)]
    with pytest.raises(ValueError, match="성별"):
        merge_rules(rules, ["a", "b"])


def test_하나만_고르면_합치지_않는다():
    with pytest.raises(ValueError, match="둘 이상"):
        merge_rules([rule("a", Gender.MALE, 1, 1)], ["a"])


def test_나누면_학년마다_부문이_되고_인원_기준_때문에_다시_합쳐지지_않는다():
    rules = [rule("a", Gender.MALE, 1, 2, min_entries=5)]
    roster = people(Gender.MALE, 1, 1, 2, 2)
    assert len(build_divisions(roster, [], rules).divisions) == 1
    split = split_rules(rules, ["a"])
    assert [(r.grade_from.value, r.grade_to.value, r.min_entries) for r in split] == [(1, 1, None), (2, 2, None)]
    assert len({r.id for r in split}) == len(split)
    assert [d.label for d in build_divisions(roster, [], split).divisions] == ["남자 초1 개인전", "남자 초2 개인전"]


def test_나눠도_혼자인_학년은_다시_합쳐진다():
    split = split_rules([rule("a", Gender.MALE, 1, 2)], ["a"])
    labels = [d.label for d in build_divisions(people(Gender.MALE, 1, 2, 2), [], split).divisions]
    assert labels == ["남자 초1~초2 개인전"]


def test_나눈_규칙_이름은_기존_규칙과_겹치지_않는다():
    rules = [rule("a", Gender.MALE, 1, 2), rule("a-2", Gender.FEMALE, 1, 1)]
    split = split_rules(rules, ["a"])
    assert len({r.id for r in split}) == len(split)
