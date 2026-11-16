from kendo_tournament.domain.division.builder import build_divisions
from kendo_tournament.domain.division.unplaced import missing_rules, unplaced_lines
from kendo_tournament.domain.model import DivisionRule, Event, Gender, Grade, Participant, Team


def person(pid, gender, grade):
    return Participant(pid, f"선수{pid}", gender, f"도장{pid}", grade=Grade(grade))


def test_단체전에_들어간_팀원은_빠진_선수로_세지_않는다():
    people = [person(f"m{i}", None, 1) for i in range(6)]
    teams = [
        Team(f"t{k}", f"도장{k} A", f"도장{k}", tuple(f"m{3 * k + i}" for i in range(3)), "초등저학년 1~3학년") for k in range(2)
    ]
    rules = [DivisionRule("단", Event.TEAM, None, Grade(1), Grade(3))]
    result = build_divisions(people, teams, rules)
    assert result.unassigned == () and result.unplaced_teams == ()


def test_빠진_선수와_팀은_이유를_묶어_알리고_부문을_만들어_해결한다():
    people = [person("a", Gender.MALE, 2), person("b", Gender.MALE, 2), person("c", Gender.FEMALE, 13)]
    people += [person(f"m{i}", Gender.MALE, 7) for i in range(3)]
    teams = [Team("t", "도장m A", "도장m", ("m0", "m1", "m2"), "남청소년부(중,고)")]
    rules = [DivisionRule("남1", Event.INDIVIDUAL, Gender.MALE, Grade(1), Grade(1))]
    result = build_divisions(people, teams, rules)
    assert {p.id for p in result.unassigned} == {"a", "b", "c"}
    assert [t.id for t in result.unplaced_teams] == ["t"]
    lines = unplaced_lines(result)
    assert any("남자 초2" in line and "2명" in line for line in lines)
    assert any("여자 성인" in line for line in lines)
    assert any("단체전" in line and "도장m A" in line for line in lines)
    fixed = rules + missing_rules(result, existing_ids=[r.id for r in rules])
    again = build_divisions(people, teams, fixed)
    assert again.unassigned == () and again.unplaced_teams == ()


def test_종별_없는_예전_팀은_팀원_성별_학년으로_부문을_만든다():
    people = [person(f"m{i}", None, 1 + i % 2) for i in range(6)]
    teams = [Team(f"t{k}", f"도장{k} A", f"도장{k}", tuple(f"m{3 * k + i}" for i in range(3))) for k in range(2)]
    result = build_divisions(people, teams, [])
    rules = missing_rules(result, participants=people)
    assert [(r.event, r.gender, r.grade_from.value, r.grade_to.value) for r in rules] == [(Event.TEAM, None, 1, 2)]
    assert build_divisions(people, teams, rules).unplaced_teams == ()
