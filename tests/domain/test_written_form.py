"""문자로 신청한 사람을 신청서 모양 화면에 직접 적는다(운영자 지시). 이름은 지어낸 것이다."""

from kendo_tournament.domain.model import Gender
from kendo_tournament.domain.written_form import IndividualLine, TeamLine, WrittenForm, split_names, written_roster


def form(individuals=(), teams=(), dojang="가람검도관"):
    return WrittenForm(dojang, tuple(individuals), tuple(teams))


def test_이름은_쉼표_띄어쓰기_줄바꿈으로_나뉜다():
    assert split_names("김하나, 이두리  박세찬\n최나래,") == ("김하나", "이두리", "박세찬", "최나래")
    assert split_names("  ") == ()


def test_개인전_줄의_이름은_종별에서_성별_학년을_받고_종별_글을_지닌다():
    roster = written_roster(form([IndividualLine("남초등 1~2학년", ("김하나", "이두리")), IndividualLine("여초등 3학년", ())]))
    assert [(p.name, p.gender, p.grade.label, p.category) for p in roster.participants] == [
        ("김하나", Gender.MALE, "초1", "남초등 1~2학년"),
        ("이두리", Gender.MALE, "초1", "남초등 1~2학년"),
    ]
    assert all(p.source == "직접 작성: 가람검도관" and p.dojang == "가람검도관" for p in roster.participants)
    assert roster.problems == ()


def test_단체전_팀은_종별과_자리를_지니고_빈_자리는_빠진다():
    team = TeamLine("초등고학년 4~6학년", "A", (("선봉", "오가온"), ("중견", ""), ("주장", "윤마루"), ("후보", "")))
    roster = written_roster(form(teams=[team]))
    (made,) = roster.teams
    assert made.name == "가람검도관 A" and made.category == "초등고학년 4~6학년"
    assert made.positions == ("선봉", "주장")
    names = {p.id: p.name for p in roster.participants}
    assert [names[m] for m in made.member_ids] == ["오가온", "윤마루"]
    assert all(p.category == "" for p in roster.participants), "단체전 팀원은 개인전 종별이 없다"


def test_이름을_하나도_안_적은_팀은_만들지_않는다():
    roster = written_roster(form(teams=[TeamLine("초등고학년 4~6학년", "B", (("선봉", ""),))]))
    assert roster.teams == () and roster.participants == () and roster.problems == ()


def test_도장이_비면_아무것도_넣지_않고_알린다():
    roster = written_roster(form([IndividualLine("남초등 1~2학년", ("김하나",))], dojang=" "))
    assert roster.participants == () and roster.problems


def test_알아볼_수_없는_종별에_적은_이름은_넣지_않고_알린다():
    roster = written_roster(form([IndividualLine("메모", ("김하나",))]))
    assert roster.participants == () and "메모" in roster.problems[0]


def test_같은_도장을_두_번_적어도_선수_id_가_같아_예전_것을_바꿀_수_있다():
    lines = [IndividualLine("남초등 1~2학년", ("김하나",))]
    assert written_roster(form(lines)).participants[0].id == written_roster(form(lines)).participants[0].id


def test_직접_작성_줄은_초등_학년_범위를_묶음_줄과_학년마다_한_줄로_둔다():
    """운영자: 1학년·2학년을 따로 적어야 할 수도, 「1~2」로 묶여 올 수도 있다. 묶음 줄이 먼저, 그 밑에 학년 줄."""
    from kendo_tournament.domain.written_form import entry_lines

    lines = entry_lines(("남초등 1~2학년", "여초등 4~6학년", "여청소년 (중,고)", "남자청년부 20~35세"))
    assert lines == (
        "남초등 1~2학년",
        "남초등 1학년",
        "남초등 2학년",
        "여초등 4~6학년",
        "여초등 4학년",
        "여초등 5학년",
        "여초등 6학년",
        "여청소년 (중,고)",
        "남자청년부 20~35세",
    )
    roster = written_roster(form([IndividualLine("남초등 2학년", ("김하나",))]))
    assert roster.participants[0].grade.label == "초2"


def test_묶음_줄에_적은_선수는_학년을_지어내지_않고_묶인_종별_그대로_남는다():
    roster = written_roster(form([IndividualLine("남초등 1~2학년", ("김둘",))]))
    assert roster.participants[0].category == "남초등 1~2학년"


def test_요강에_없는_묶음은_직접_적은_종별로_넣는다():
    """요강이 학년마다 따로여도 「초1~2」로 묶인 신청이 온다. 창의 「다른 종별 직접 적기」 줄은 종별 글을 그대로 넘긴다."""
    roster = written_roster(form([IndividualLine("남초등 1~2학년", ("김셋",)), IndividualLine("알 수 없음", ("김넷",))]))
    assert [p.name for p in roster.participants] == ["김셋"]
    assert roster.problems
