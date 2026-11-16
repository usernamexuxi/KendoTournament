from kendo_tournament.domain.division.builder import build_divisions
from kendo_tournament.domain.draw.bracket import pass_count
from kendo_tournament.domain.model import DivisionRule, Event, Gender, Grade, Participant

MIDDLE_1, MIDDLE_2, MIDDLE_3 = 7, 8, 9


def people(gender, grade_value, count):
    return [Participant(f"{grade_value}-{i}", f"선수{i}", gender, "A관", grade=Grade(grade_value)) for i in range(count)]


def rule(rid, gender, grade_value):
    return DivisionRule(rid, Event.INDIVIDUAL, gender, Grade(grade_value), Grade(grade_value))


def report_for(groups):
    roster, rules = [], []
    for grade_value, count in groups:
        roster += people(Gender.FEMALE, grade_value, count)
        rules.append(rule(f"f{grade_value}", Gender.FEMALE, grade_value))
    return build_divisions(roster, [], rules)


def test_부전승_횟수는_라운드마다_홀수로_남을_때만_센다():
    assert [pass_count(n) for n in (1, 2, 4, 8, 16)] == [0, 0, 0, 0, 0]
    assert pass_count(10) == 2
    assert pass_count(5) == 2
    assert pass_count(6) == 1


def test_부전승이_있지만_합칠_이웃이_없으면_그대로_둘_부문으로_알린다():
    result = report_for([(MIDDLE_3, 10)])
    assert [size.label for size in result.byes.keep] == ["여자 중3 개인전"]
    assert result.byes.keep[0].passes == 2
    assert result.byes.merges == ()


def test_부전승이_없으면_점검할_것이_없다():
    assert not report_for([(MIDDLE_3, 8)]).byes.has_byes


def test_이웃_학년과_합쳐_부전승이_줄면_그_짝을_추천하고_마음대로_합치지_않는다():
    result = report_for([(MIDDLE_2, 6), (MIDDLE_3, 10)])
    (advice,) = result.byes.merges
    assert advice.labels == ("여자 중2 개인전", "여자 중3 개인전")
    assert (advice.merged_count, advice.before, advice.after) == (16, 3, 0)
    assert result.byes.keep == ()
    assert len(result.divisions) == 2


def test_합쳐도_나아지지_않으면_추천하지_않는다():
    result = report_for([(MIDDLE_2, 4), (MIDDLE_3, 6)])
    assert result.byes.merges == ()


def test_한_부문은_추천_하나에만_든다():
    result = report_for([(MIDDLE_1, 5), (MIDDLE_2, 7), (MIDDLE_3, 9)])
    labels = [label for advice in result.byes.merges for label in advice.labels]
    assert len(labels) == len(set(labels))
    assert result.byes.merges


def test_학교급을_넘는_합치기는_권하지_않는다():
    elementary_6 = 6
    result = report_for([(elementary_6, 6), (MIDDLE_1, 10)])
    assert result.byes.merges == ()
