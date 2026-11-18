from kendo_tournament.domain.division.builder import build_divisions
from kendo_tournament.domain.division.team_categories import team_rules
from kendo_tournament.domain.model import Event, Gender, Grade, Participant, Team

KINDS = ("초등저학년 1~3학년", "초등고학년 4~6학년", "여청소년부(중,고)", "남청소년부(중,고)", "남자일반부")
GRADE_OF = {KINDS[0]: 1, KINDS[1]: 4, KINDS[2]: 7, KINDS[3]: 7, KINDS[4]: 13}
GENDER_OF = {KINDS[2]: Gender.FEMALE, KINDS[3]: Gender.MALE, KINDS[4]: Gender.MALE}


def roster():
    people, teams = [], []
    for k, kind in enumerate(KINDS):
        for d in range(2):
            ids = tuple(f"p{k}{d}{m}" for m in range(3))
            people += [Participant(i, f"선수{i}", GENDER_OF.get(kind), f"도장{d}", grade=Grade(GRADE_OF[kind])) for i in ids]
            teams.append(Team(f"t{k}{d}", f"도장{d} A", f"도장{d}", ids, category=kind))
    return people, teams


def test_신청서_팀_종별마다_단체전_규칙이_하나씩_생긴다():
    _, teams = roster()
    rules = team_rules(teams)
    assert [(r.gender, r.grade_from.value, r.grade_to.value) for r in rules] == [
        (None, 1, 3),
        (None, 4, 6),
        (Gender.FEMALE, 7, 12),
        (Gender.MALE, 7, 12),
        (Gender.MALE, 13, 13),
    ]
    assert all(r.event is Event.TEAM for r in rules)
    assert len({r.id for r in team_rules(teams, existing_ids=["r1", "r2"])} | {"r1", "r2"}) == 7


def test_팀은_자기_종별_부문에만_들어간다():
    people, teams = roster()
    result = build_divisions(people, teams, team_rules(teams))
    placed = {d.label: sorted(e.id for e in d.entries) for d in result.divisions}
    assert placed == {
        "혼성 초등 저학년부 단체전": ["t00", "t01"],
        "혼성 초등 고학년부 단체전": ["t10", "t11"],
        "여자 중1~고3 단체전": ["t20", "t21"],
        "남자 중1~고3 단체전": ["t30", "t31"],
        "남자 성인 단체전": ["t40", "t41"],
    }


def test_혼성_부문에는_남자_팀이_섞이지_않는다():
    people, teams = roster()
    mixed_youth = [r for r in team_rules(teams) if r.gender is None][:1]
    boys = [t for t in teams if t.category == KINDS[3]]
    result = build_divisions(people, boys, mixed_youth)
    assert all(not d.entries for d in result.divisions)


def test_나이_없는_성인_단체전_종별은_부_이름으로_나뉘고_팀은_같은_이름_부문에만_든다():
    from kendo_tournament.domain.division.category_table import INJE_NATIONAL

    rules = team_rules([], labels=INJE_NATIONAL.team)
    labels = [rule.label for rule in rules]
    assert len(labels) == len(set(labels)) == len(INJE_NATIONAL.team)
    assert "혼성 중년부 단체전" in labels and "혼성 청년부 단체전" in labels
    people = [Participant(f"m{i}", f"선수{i}", Gender.MALE, "도장", grade=Grade(13), age=45) for i in range(3)]
    middle_aged = Team("t", "도장 A", "도장", tuple(p.id for p in people), category="중년부")
    result = build_divisions(people, [middle_aged], rules)
    assert [(d.label, [e.id for e in d.entries]) for d in result.divisions] == [("혼성 중년부 단체전", ["t"])]


def test_신청서_종별의_부_이름을_뽑는다():
    from kendo_tournament.domain.division.category_label import band_name

    assert band_name("남자청년부 20~35세") == "청년부"
    assert band_name("40대 중년부") == "중년부"
    assert band_name("50대이상 노년부") == "노년부"
    assert band_name("중년부") == "중년부"
