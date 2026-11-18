from kendo_tournament.domain.division.category_table import GWANGMYEONG_CHAIRMAN
from kendo_tournament.domain.division.presets import PresetChoice, level_title, make_rules
from kendo_tournament.domain.model import Event, Grade


def test_고른_종목마다_종별_표대로_규칙을_만들고_id는_겹치지_않는다():
    rules = make_rules(PresetChoice((Event.INDIVIDUAL, Event.TEAM)), existing_ids=["r1"])
    assert "r1" not in {r.id for r in rules}
    assert len({r.id for r in rules}) == len(rules)
    individual = [r for r in rules if r.event is Event.INDIVIDUAL]
    team = [r for r in rules if r.event is Event.TEAM]
    assert len(individual) == len(GWANGMYEONG_CHAIRMAN.individual)
    assert len(team) == len(GWANGMYEONG_CHAIRMAN.team)


def test_고르지_않은_종목은_규칙을_만들지_않는다():
    assert all(r.event is Event.INDIVIDUAL for r in make_rules(PresetChoice((Event.INDIVIDUAL,))))


def test_인원_기준은_모든_규칙에_붙는다():
    assert {r.min_entries for r in make_rules(PresetChoice((Event.INDIVIDUAL, Event.TEAM), min_entries=4))} == {4}


def test_단체전_규칙은_대회_종별_표_순서대로_먼저_생기고_팀_신청서에만_있는_종별이_뒤에_붙는다():
    from kendo_tournament.domain.model import Team

    teams = [Team("t1", "가 A", "가", ("p",), "남자 성인부"), Team("t2", "나 A", "나", ("q",), "여초등 1~3학년")]
    labels = [r.label for r in make_rules(PresetChoice((Event.TEAM,)), teams=teams)]
    assert labels[0] == "혼성 초등 저학년부 단체전"
    assert labels[len(GWANGMYEONG_CHAIRMAN.team) - 1] == "남자 성인 단체전"
    assert labels[len(GWANGMYEONG_CHAIRMAN.team) :] == ["여자 초1~초3 단체전"]


def test_중등과_고등에_걸친_부문의_쪽_제목은_중고등부():
    assert level_title(Grade(7), Grade(12)) == "중고등부"
    assert level_title(Grade(9), Grade(10)) == "중고등부"
    assert level_title(Grade(7), Grade(9)) == "중등부"
    assert level_title(Grade(1), Grade(1)) == "초등부"
