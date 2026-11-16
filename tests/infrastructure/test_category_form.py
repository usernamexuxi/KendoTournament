from kendo_tournament.domain.model import Gender
from kendo_tournament.infrastructure.readers.document_text import Paragraph, Table, blocks_to_result

HEAD = (("단 체 명", "가람검도관", "주    소", "어딘가"), ("대 표 자", "", "전화", ""))
GRID = (
    ("종 별", "성   명", "성   명", "성   명"),
    ("남초등 1~2학년", "김하나", "이두리", ""),
    ("", "박세찬", "", ""),
    ("여청소년 (중,고)", "최나래", "", ""),
    ("중등부", "정다온", "", ""),
    ("남자청년부 20~35세", "한바다", "", ""),
)
TEAM_KIND = (("팀별", "초등고학년 4~6학년"),)
TEAMS = (
    ("A팀", "성   명", "생년 월일", "B팀", "성   명", "생년 월일"),
    ("선봉", "오가온", "16.10.03", "선봉", "", ""),
    ("중견", "윤마루", "15.04.15", "중견", "", ""),
)


def test_종별_성명_모양_신청서에서_종별로_성별_학년_나이를_채운다():
    result = blocks_to_result([Table(HEAD), Table(GRID)], "가람.hwp")
    people = {p.name: p for p in result.participants}
    assert set(people) == {"김하나", "이두리", "박세찬", "최나래", "정다온", "한바다"}
    assert all(p.dojang == "가람검도관" for p in people.values())
    assert people["박세찬"].grade.label == "초1" and people["박세찬"].gender is Gender.MALE
    assert people["최나래"].gender is Gender.FEMALE and people["최나래"].grade.label == "중1"
    assert people["정다온"].gender is Gender.MALE
    assert people["한바다"].grade.label == "성인" and people["한바다"].age == 20
    assert result.problems == ()


def test_단체전_표는_앞_종별로_팀을_만들고_빈_팀은_건너뛴다():
    result = blocks_to_result([Table(HEAD), Paragraph("※ 단체전 남, 여 혼성"), Table(TEAM_KIND), Table(TEAMS)], "가람.hwp")
    assert [team.name for team in result.teams] == ["가람검도관 A"]
    members = [p for p in result.participants if p.id in result.teams[0].member_ids]
    assert {p.name for p in members} == {"오가온", "윤마루"}
    assert all(p.gender is None and p.grade.label == "초4" for p in members)


def test_단체전_종별을_고를_수_없으면_알리고_팀은_넣지_않는다():
    unclear = (("팀별", "여청소년부(중,고)     남청소년부(중,고)   남자일반부"),)
    result = blocks_to_result([Table(HEAD), Table(unclear), Table(TEAMS)], "가람.hwp")
    assert result.teams == ()
    assert any("단체전 종별" in problem for problem in result.problems)


def test_종별마다_따로_있는_단체전_표의_A팀끼리_겹치지_않는다():
    low = (("팀별", "초등저학년1~3학년"),)
    blocks = [Table(HEAD), Table(TEAM_KIND), Table(TEAMS), Table(low), Table(TEAMS)]
    result = blocks_to_result(blocks, "가람.hwp")
    assert len(result.teams) == 2
    assert len({team.id for team in result.teams}) == 2


def test_단체전_팀은_팀별_칸에서_고른_종별을_지닌다():
    result = blocks_to_result([Table(HEAD), Table(TEAM_KIND), Table(TEAMS)], "가람.hwp")
    assert [team.category for team in result.teams] == ["초등고학년 4~6학년"]


def test_개인전_선수는_종별_글을_지니고_단체전_팀원은_비워_둔다():
    blocks = [Table(HEAD), Table(GRID), Paragraph("※ 단체전 남, 여 혼성"), Table(TEAM_KIND), Table(TEAMS)]
    people = {p.name: p for p in blocks_to_result(blocks, "가람.hwp").participants}
    assert people["박세찬"].category == "남초등 1~2학년"
    assert people["한바다"].category == "남자청년부 20~35세"
    assert people["오가온"].category == ""


def test_쪽_제목에_적힌_단체전_종별로_팀을_만든다():
    blocks = [Table(HEAD), Paragraph("참가신청서(단체전/초등/저학년부)"), Paragraph("※ 단체전"), Table(TEAMS)]
    result = blocks_to_result(blocks, "가람.hwp")
    assert [team.category for team in result.teams] == ["초등 저학년부"]
    assert result.problems == ()


def test_팀별_칸의_종별_여럿은_팀_묶음_순서대로_붙는다():
    kinds = (("팀별", "여청소년부(중,고)     남청소년부(중,고)   남자일반부"),)
    three = (
        ("A팀", "성   명", "생년 월일", "A팀", "성   명", "생년 월일", "A팀", "성   명", "생년 월일"),
        ("선봉", "오가온", "111008", "선봉", "윤마루", "100121", "선봉", "한바다", "890407"),
    )
    result = blocks_to_result([Table(HEAD), Table(kinds), Table(three)], "가람.hwp")
    assert [team.category for team in result.teams] == ["여청소년부(중,고)", "남청소년부(중,고)", "남자일반부"]
    assert len({team.id for team in result.teams}) == 3


def test_팀별_칸의_종별_수가_팀_묶음과_다르면_알린다():
    kinds = (("팀별", "초등저학년1~3학년   초등고학년 4~6학년   남자일반부"),)
    result = blocks_to_result([Table(HEAD), Table(kinds), Table(TEAMS)], "가람.hwp")
    assert result.teams == ()
    assert result.problems


def test_요강의_빈_신청서_양식에서_종별_표를_읽는다():
    kinds = (("팀별", "초등저학년1~3학년   초등고학년 4~6학년   남청소년부(중,고) 여청소년부(중,고)     남자일반부"),)
    blank_grid = (("종 별", "성   명", "성   명"), ("남초등 1~2학년", "", ""), ("", "", ""), ("여자일반부", "", ""))
    empty_teams = (("A팀", "성   명", "생년 월일", "B팀", "성   명", "생년 월일"), ("선봉", "", "", "선봉", "", ""))
    result = blocks_to_result([Table(kinds), Table(empty_teams), Table(blank_grid)], "요강.hwp")
    assert result.form_categories.individual == ("남초등 1~2학년", "여자일반부")
    assert result.form_categories.team == (
        "초등저학년1~3학년",
        "초등고학년 4~6학년",
        "남청소년부(중,고)",
        "여청소년부(중,고)",
        "남자일반부",
    )
    assert result.participants == () and result.problems == ()


def test_신청서_양식이_없는_문서는_종별_표가_없다():
    assert blocks_to_result([Paragraph("대회 요강"), Table(HEAD)], "공문.hwp").form_categories is None


def test_종별이_위_칸이고_이름이_아래로_늘어선_전국대회_양식을_읽는다():
    head = ("번호", "1,2학년", "3,4학년", "여중부", "여자부", "40대 중년부")
    grid = (head, ("1", "김하나", "", "", "최나래", "한바다"), ("2", "이두리", "박세찬", "", "", ""))
    result = blocks_to_result([Table(HEAD), Table(grid)], "인제.hwp")
    people = {p.name: p for p in result.participants}
    assert set(people) == {"김하나", "이두리", "박세찬", "최나래", "한바다"}
    assert people["박세찬"].category == "3,4학년" and people["박세찬"].grade.label == "초3"
    assert people["최나래"].gender is Gender.FEMALE
    assert people["한바다"].gender is Gender.MALE and people["한바다"].age == 40
    assert result.form_categories.individual == head[1:]


def test_단체전_종별을_괄호_한_줄로_적은_양식도_팀을_만든다():
    blocks = [Table(HEAD), Paragraph("※ 단체전  ( 중년부 )"), Table(TEAMS)]
    result = blocks_to_result(blocks, "인제.hwp")
    assert [team.category for team in result.teams] == ["중년부"]
    assert result.problems == ()


def test_단체전_팀원은_신청서의_자리를_지니고_빈_자리가_있어도_밀리지_않는다():
    gap = (
        ("A팀", "성   명", "생년 월일"),
        ("선봉", "오가온", ""),
        ("중견", "", ""),
        ("주장", "윤마루", ""),
        ("후보", "서다인", ""),
    )
    result = blocks_to_result([Table(HEAD), Table(TEAM_KIND), Table(gap)], "가람.hwp")
    team = result.teams[0]
    names = {p.id: p.name for p in result.participants}
    assert [(position, names[member]) for position, member in zip(team.positions, team.member_ids, strict=True)] == [
        ("선봉", "오가온"),
        ("주장", "윤마루"),
        ("후보", "서다인"),
    ]
