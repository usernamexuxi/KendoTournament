from kendo_tournament.domain.division.builder import build_divisions
from kendo_tournament.domain.model import DivisionRule, Event, Gender, Grade, Participant, Team


def person(pid, gender, grade_value, dojang="A관"):
    return Participant(pid, f"선수{pid}", gender, dojang, grade=Grade(grade_value))


def rule(rid, gender, start, end, min_entries=None, event=Event.INDIVIDUAL, team_size=None):
    return DivisionRule(rid, event, gender, Grade(start), Grade(end), team_size, min_entries)


def test_규칙마다_성별과_구분범위로_나눈다():
    people = [person("1", Gender.MALE, 1), person("2", Gender.MALE, 2), person("3", Gender.FEMALE, 1)]
    result = build_divisions(people, [], [rule("m12", Gender.MALE, 1, 2), rule("f1", Gender.FEMALE, 1, 1)])
    assert [d.label for d in result.divisions] == ["남자 초1~초2 개인전", "여자 초1 개인전"]
    assert [len(d.entries) for d in result.divisions] == [2, 1]
    assert result.unassigned == ()


def test_혼성_규칙은_성별을_가리지_않는다():
    people = [person("1", Gender.MALE, 13), person("2", Gender.FEMALE, 13)]
    result = build_divisions(people, [], [rule("mix", None, 13, 13)])
    assert len(result.divisions[0].entries) == 2
    assert result.divisions[0].label == "혼성 성인 개인전"


def test_기준_미달이면_위_부문과_합친다():
    people = [person("1", Gender.MALE, 1)] + [person(str(i), Gender.MALE, 2) for i in range(2, 6)]
    rules = [rule("r1", Gender.MALE, 1, 1, 3), rule("r2", Gender.MALE, 2, 2)]
    result = build_divisions(people, [], rules)
    assert [d.label for d in result.divisions] == ["남자 초1~초2 개인전"]
    assert result.divisions[0].rule_ids == ("r1", "r2")
    assert len(result.divisions[0].entries) == 5


def test_합친_뒤에도_모자라면_한번_더_합친다():
    people = [person("1", Gender.MALE, 1), person("2", Gender.MALE, 2), person("3", Gender.MALE, 3)]
    rules = [rule("r1", Gender.MALE, 1, 1, 3), rule("r2", Gender.MALE, 2, 2), rule("r3", Gender.MALE, 3, 3)]
    result = build_divisions(people, [], rules)
    assert [d.label for d in result.divisions] == ["남자 초1~초3 개인전"]


def test_다른_성별과는_합치지_않고_경고한다():
    people = [person("1", Gender.MALE, 1), person("2", Gender.FEMALE, 2)]
    rules = [rule("r1", Gender.MALE, 1, 1, 3), rule("r2", Gender.FEMALE, 2, 2)]
    result = build_divisions(people, [], rules)
    assert len(result.divisions) == 2
    assert "합칠 종별이 없습니다" in result.warnings[0]


def test_위_학년이_없으면_아래로_합친다():
    people = [person("1", Gender.MALE, 4), person("2", Gender.MALE, 5), person("3", Gender.MALE, 6)]
    rules = [rule("r1", Gender.MALE, 4, 5), rule("r2", Gender.MALE, 6, 6, 2)]
    result = build_divisions(people, [], rules)
    assert [d.label for d in result.divisions] == ["남자 초4~초6 개인전"]


def test_어느_부문에도_안_든_선수와_두_부문에_든_선수를_알린다():
    people = [person("1", Gender.MALE, 1), person("2", Gender.MALE, 9)]
    rules = [rule("a", Gender.MALE, 1, 2), rule("b", None, 1, 1)]
    result = build_divisions(people, [], rules)
    assert [p.id for p in result.unassigned] == ["2"]
    assert [p.id for p in result.multi_assigned] == ["1"]


def test_단체전은_팀원이_모두_범위_안일_때만_든다():
    people = [person("1", Gender.MALE, 13), person("2", Gender.MALE, 13), person("3", Gender.MALE, 12)]
    teams = [Team("t1", "A관 A팀", "A관", ("1", "2")), Team("t2", "A관 B팀", "A관", ("1", "3"))]
    rules = [rule("team", Gender.MALE, 13, 13, event=Event.TEAM, team_size=2)]
    result = build_divisions(people, teams, rules)
    assert [e.id for e in result.divisions[0].entries] == ["t1"]


def test_혼자인_부문은_합치기를_안_정해도_위_학년과_합친다():
    people = [person("1", Gender.MALE, 1), person("2", Gender.MALE, 2), person("3", Gender.MALE, 2)]
    result = build_divisions(people, [], [rule("r1", Gender.MALE, 1, 1), rule("r2", Gender.MALE, 2, 2)])
    assert [d.label for d in result.divisions] == ["남자 초1~초2 개인전"]
    assert all(len(d.entries) >= 2 for d in result.divisions)


def test_혼자인_부문이_맨_위_학년이면_아래_학년과_합친다():
    people = [person("1", Gender.MALE, 4), person("2", Gender.MALE, 4), person("3", Gender.MALE, 5)]
    result = build_divisions(people, [], [rule("r4", Gender.MALE, 4, 4), rule("r5", Gender.MALE, 5, 5)])
    assert [d.label for d in result.divisions] == ["남자 초4~초5 개인전"]


def test_위아래_이웃이_다_있으면_인원이_적은_쪽과_합친다():
    people = [person(pid, Gender.MALE, grade) for pid, grade in (("1", 1), ("2", 1), ("3", 1), ("4", 2), ("5", 3), ("6", 3))]
    rules = [rule("r1", Gender.MALE, 1, 1), rule("r2", Gender.MALE, 2, 2, 2), rule("r3", Gender.MALE, 3, 3)]
    result = build_divisions(people, [], rules)
    assert [d.label for d in result.divisions] == ["남자 초1 개인전", "남자 초2~초3 개인전"]


def test_인원_기준에_못_미치면_옆_학년과_합친다():
    people = [person(str(i), Gender.MALE, 1 if i < 2 else 2) for i in range(6)]
    rules = [rule("r1", Gender.MALE, 1, 1, 3), rule("r2", Gender.MALE, 2, 2)]
    result = build_divisions(people, [], rules)
    assert [d.label for d in result.divisions] == ["남자 초1~초2 개인전"]


def test_바로_위_학년이_비어_있으면_그다음_학년까지_합친다():
    people = [person("1", Gender.MALE, 1), person("2", Gender.MALE, 3)]
    rules = [rule("r1", Gender.MALE, 1, 1), rule("r2", Gender.MALE, 2, 2), rule("r3", Gender.MALE, 3, 3)]
    result = build_divisions(people, [], rules)
    assert [d.label for d in result.divisions] == ["남자 초1~초3 개인전"]


def test_혼자인데_합칠_부문이_없으면_경고한다():
    result = build_divisions([person("1", Gender.FEMALE, 1)], [], [rule("f1", Gender.FEMALE, 1, 1)])
    assert len(result.divisions[0].entries) == 1
    assert any("혼자" in warning for warning in result.warnings)


def test_학교급이_같은_이웃을_먼저_고른다():
    grades = (("1", 11), ("2", 11), ("3", 11), ("4", 12), ("5", 13), ("6", 13))
    people = [person(pid, Gender.MALE, grade) for pid, grade in grades]
    rules = [rule(f"r{g}", Gender.MALE, g, g) for g in (11, 12, 13)]
    result = build_divisions(people, [], rules)
    assert [d.label for d in result.divisions] == ["남자 고2~고3 개인전", "남자 성인 개인전"]


def test_혼자인데_사람이_있는_이웃이_없으면_빈_부문과_합치지_않고_경고만_한다():
    people = [person("1", Gender.MALE, 5)]
    rules = [rule(f"r{g}", Gender.MALE, g, g) for g in range(1, 14)]
    result = build_divisions(people, [], rules)
    assert [d.label for d in result.divisions] == ["남자 초5 개인전"]
    assert any("합칠 종별이 없습니다" in warning for warning in result.warnings)


def test_단체전_팀_인원은_신청서대로라_3명_팀과_4명_팀이_한_부문에_든다():
    from kendo_tournament.domain.model import Team

    people = [Participant(f"p{i}", f"선수{i}", Gender.MALE, f"도장{i // 4}", grade=Grade(13)) for i in range(7)]
    teams = [Team("t0", "도장0 A", "도장0", ("p0", "p1", "p2", "p3")), Team("t1", "도장1 A", "도장1", ("p4", "p5", "p6"))]
    rules = [DivisionRule("단", Event.TEAM, Gender.MALE, Grade(13), Grade(13))]
    result = build_divisions(people, teams, rules)
    assert [len(d.entries) for d in result.divisions] == [2]


def test_단체전_부문에_한_팀뿐이면_다른_부문과_합치지_않고_경기가_없다고_알린다():
    """운영자: 단체전은 말을 맞추고 나와 보통 상대가 있다. 혼자면 경기를 못 하는 것이니 합치지 말고 알린다."""
    from kendo_tournament.domain.model import DivisionRule, Event, Gender, Grade, Participant, Team

    people = [Participant(f"p{i}", f"선수{i}", Gender.FEMALE, "도장", Grade(8 if i < 3 else 13)) for i in range(6)]
    teams = [
        Team("t1", "가 A", "가", ("p0", "p1", "p2"), "여청소년부(중,고)"),
        Team("t2", "나 A", "나", ("p3", "p4", "p5"), "여자일반부"),
    ]
    rules = [
        DivisionRule("y", Event.TEAM, Gender.FEMALE, Grade(7), Grade(12)),
        DivisionRule("a", Event.TEAM, Gender.FEMALE, Grade(13), Grade(13)),
    ]
    result = build_divisions(people, teams, rules)
    assert sorted((d.label, len(d.entries)) for d in result.divisions) == [
        ("여자 성인 단체전", 1),
        ("여자 중1~고3 단체전", 1),
    ]
    alone = [w for w in result.warnings if "1팀뿐" in w]
    assert len(alone) == 2
