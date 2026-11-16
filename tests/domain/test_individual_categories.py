from kendo_tournament.domain.division.builder import build_divisions
from kendo_tournament.domain.division.category_table import DEFAULT_CATEGORY_TABLE
from kendo_tournament.domain.division.individual_categories import individual_rules
from kendo_tournament.domain.division.presets import PresetChoice, make_rules
from kendo_tournament.domain.model import DivisionRule, Event, Gender, Grade, Participant, Team

MALE, FEMALE = Gender.MALE, Gender.FEMALE


def person(pid: str, category: str, gender: Gender | None, grade: int, age: int | None = None) -> Participant:
    """신청서 리더가 만드는 모양 그대로: 학년·나이는 종별 범위의 첫 값이다."""
    return Participant(pid, f"선수{pid}", gender, f"도장{pid}", Grade(grade), age, category=category)


def form_roster() -> list[Participant]:
    return [
        person("a", "남초등 1~2학년", MALE, 1),
        person("b", "남초등 1~2학년", MALE, 1),
        person("c", "남초등 3~4학년", MALE, 3),
        person("d", "남초등 5~6학년", MALE, 5),
        person("e", "여초등 1~3학년", FEMALE, 1),
        person("f", "여청소년 (중,고)", FEMALE, 7),
        person("g", "중등부", MALE, 7),
        person("h", "남자청년부 20~35세", MALE, 13, 20),
        person("i", "남자중년부 48세부터", MALE, 13, 48),
    ]


def test_기본_개인전_규칙은_신청서_종별_12개를_그_순서로_만든다():
    labels = [rule.label for rule in individual_rules([])]
    assert labels == [
        "남자 초1~초2 개인전",
        "남자 초3~초4 개인전",
        "남자 초5~초6 개인전",
        "여자 초1~초3 개인전",
        "여자 초4~초6 개인전",
        "여자 중1~고3 개인전",
        "남자 중1~중3 개인전",
        "남자 고1~고3 개인전",
        "남자 청년부(20~35세) 개인전",
        "남자 장년부(36~47세) 개인전",
        "남자 중년부(48세부터) 개인전",
        "여자 성인 개인전",
    ]


def old_form_adults() -> list[Participant]:
    """광명인화검도관 신청서처럼 요강과 다른 나이 구간을 적은 양식."""
    return [
        person("y1", "남자청년부 20~29세", MALE, 13, 20),
        person("y2", "남자장년부 30~39세", MALE, 13, 30),
        person("y3", "남자중년부 40~50세이상", MALE, 13, 40),
    ]


def test_기본_부문에_안_드는_다른_양식_종별만_뒤에_더한다():
    labels = [rule.label for rule in individual_rules([*form_roster(), *old_form_adults()])]
    assert labels[len(DEFAULT_CATEGORY_TABLE.individual) :] == ["남자 장년부(30~39세) 개인전", "남자 중년부(40세부터) 개인전"]


def test_다른_나이_구간_선수도_두_부문에_들지_않는다():
    roster = old_form_adults()
    result = build_divisions(roster, [], individual_rules(roster))
    placed = {d.label: [e.id for e in d.entries] for d in result.divisions}
    assert placed["남자 청년부(20~35세) 개인전"] == ["y1"]
    assert result.multi_assigned == () and result.unassigned == ()


def test_종별_부문에_신청서_종별_선수가_모두_들어간다():
    result = build_divisions(form_roster(), [], individual_rules(form_roster()))
    placed = {d.label: sorted(e.id for e in d.entries) for d in result.divisions}
    assert placed["남자 초1~초2 개인전"] == ["a", "b"]
    assert result.unassigned == ()
    assert result.multi_assigned == ()


def test_1_2학년_종별_선수는_초1_만의_부문에_넣지_않는다():
    """신청서는 학년을 안 적어 학년이 범위의 첫 값(초1)일 뿐이다. 초2 일 수도 있어 초1 단독 부문에 넣으면 틀린다."""
    only_first = DivisionRule("r1", Event.INDIVIDUAL, MALE, Grade(1), Grade(1))
    result = build_divisions([person("a", "남초등 1~2학년", MALE, 1)], [], [only_first])
    assert result.divisions == ()


def test_종별_없는_선수는_학년으로_부문을_찾는다():
    plain = Participant("z", "선수z", MALE, "도장z", Grade(2))
    result = build_divisions([plain], [], [DivisionRule("r1", Event.INDIVIDUAL, MALE, Grade(2), Grade(2))])
    assert [e.id for e in result.divisions[0].entries] == ["z"]


def preset() -> PresetChoice:
    return PresetChoice((Event.INDIVIDUAL,))


def test_빠른_설정은_신청서_종별이_있으면_개인전을_종별대로_만든다():
    rules = make_rules(preset(), participants=form_roster())
    assert "남자 초1~초2 개인전" in [r.label for r in rules]
    assert "남자 초2 개인전" not in [r.label for r in rules]


def test_기본_종별에_드는_직접_입력_선수에게는_학년_규칙을_더하지_않는다():
    roster = [*form_roster(), Participant("z", "선수z", MALE, "도장z", Grade(2))]
    rules = make_rules(preset(), participants=roster)
    assert "남자 초2 개인전" not in [r.label for r in rules]
    result = build_divisions(roster, [], rules)
    assert result.unassigned == () and result.multi_assigned == ()


def test_종별_표에_안_드는_선수는_빠진_선수로_남아_알린다():
    from kendo_tournament.domain.division.unplaced import unplaced_lines

    unknown_gender = Participant("z", "선수z", None, "도장z", Grade(2))
    roster = [*form_roster(), unknown_gender]
    result = build_divisions(roster, [], make_rules(preset(), participants=roster))
    assert [p.id for p in result.unassigned] == ["z"]
    assert "성별이나 학년을 몰라" in unplaced_lines(result)[0]


def test_단체전_팀원은_종별이_있어도_개인전_규칙을_만들지_않는다():
    member = person("m", "초등저학년 1~3학년", None, 1)
    team = Team("t", "도장m A", "도장m", ("m",), category="초등저학년 1~3학년")
    rules = make_rules(preset(), participants=[*form_roster(), member], teams=[team])
    assert all(r.gender is not None for r in rules)


def test_빠진_종별_선수는_자기_종별_부문으로_되살린다():
    from kendo_tournament.domain.division.unplaced import missing_rules, unplaced_lines

    only_first = DivisionRule("r1", Event.INDIVIDUAL, MALE, Grade(1), Grade(1))
    roster = [person("a", "남초등 1~2학년", MALE, 1)]
    result = build_divisions(roster, [], [only_first])
    assert "남초등 1~2학년" in unplaced_lines(result)[0]
    added = missing_rules(result, ["r1"], roster)
    assert [rule.label for rule in added] == ["남자 초1~초2 개인전"]
    assert build_divisions(roster, [], [only_first, *added]).unassigned == ()


def test_두_양식의_중년부에_다_들면_범위가_좁은_부문에_든다():
    roster = [person("o1", "남자중년부 48세부터", MALE, 13, 48), *old_form_adults()]
    result = build_divisions(roster, [], individual_rules(roster))
    placed = {d.label: [e.id for e in d.entries] for d in result.divisions}
    assert placed["남자 중년부(48세부터) 개인전"] == ["o1"]
    assert placed["남자 중년부(40세부터) 개인전"] == ["y3"]
    assert result.multi_assigned == ()


def test_종별_신청서_단체전_팀원은_개인전_부문에_들지_않는다():
    member = Participant("m", "선수m", MALE, "도장m", Grade(7))
    team = Team("t", "도장m A", "도장m", ("m",), category="남청소년부(중,고)")
    result = build_divisions([member], [team], individual_rules([member]))
    assert all(d.event is Event.TEAM for d in result.divisions)
    assert result.unassigned == ()


def test_혼자인_나이_구간_부문은_고등부와_합치지_않는다():
    roster = [
        person("h1", "고등부", MALE, 10),
        person("h2", "고등부", MALE, 10),
        person("y3", "남자중년부 40~50세이상", MALE, 13, 40),
    ]
    result = build_divisions(roster, [], individual_rules(roster))
    placed = {d.label: sorted(e.id for e in d.entries) for d in result.divisions}
    assert placed["남자 고1~고3 개인전"] == ["h1", "h2"]
    assert placed["남자 중년부(40세부터) 개인전"] == ["y3"]
    assert any("중년부" in warning for warning in result.warnings)
