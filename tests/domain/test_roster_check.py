from kendo_tournament.domain.model import Gender, Grade, Participant
from kendo_tournament.domain.roster_check import missing_fields


def person(**changes):
    values = {"id": "p", "name": "가나다", "gender": Gender.MALE, "dojang": "가관", "grade": Grade(3), "age": None}
    values.update(changes)
    return Participant(**values)


def test_다_채워지면_빠진_항목이_없다():
    assert missing_fields(person()) == []


def test_학년이_없어도_나이가_있으면_된다():
    assert missing_fields(person(grade=None, age=30)) == []


def test_빠진_항목을_모두_알린다():
    assert missing_fields(person(name=" ", dojang="", gender=None, grade=None, age=None)) == [
        "이름",
        "도장",
        "성별",
        "학년 또는 나이(8세 이상)",
    ]


def test_8세_미만_나이만_있으면_판단할_수_없다():
    assert missing_fields(person(grade=None, age=6)) == ["학년 또는 나이(8세 이상)"]


def test_혼성_단체전_팀원은_성별이_없어도_빠진_항목이_아니다():
    assert missing_fields(person(gender=None), mixed_team_member=True) == []
    assert missing_fields(person(gender=None)) == ["성별"]


def test_성별_없는_개인전_선수는_신청서마다_묶어_다시_요청하라고_알린다():
    from kendo_tournament.domain.model import Team
    from kendo_tournament.domain.roster_check import missing_gender_requests

    people = [
        person(id="a", name="홍길동", gender=None, source="가.hwpx"),
        person(id="b", name="김철수", gender=None, source="가.hwpx"),
        person(id="c", name="이영희", gender=None, source="나.pdf", dojang="나관"),
        person(id="d", name="박팀원", gender=None, source="가.hwpx"),
        person(id="e", name="최남자", source="가.hwpx"),
    ]
    teams = [Team("t", "가관 A", "가관", ("d",))]
    lines = missing_gender_requests(people, teams)
    assert len(lines) == 2
    assert "가관" in lines[0] and "가.hwpx" in lines[0] and "홍길동, 김철수" in lines[0] and "2명" in lines[0]
    assert "다시 알려 달라고 요청" in lines[0]
    assert "이영희" in lines[1] and "박팀원" not in " ".join(lines)


def test_한_신청서_두_종별_중복은_종별을_적어_서류_확인을_권한다():
    from kendo_tournament.domain.roster_check import duplicate_check_requests

    a = Participant("a", "김하나", Gender.FEMALE, "가람검도관", source="가람.hwp", category="여초등 1~3학년부")
    b = Participant("b", "김하나", Gender.FEMALE, "가람검도관", source="가람.hwp", category="여초등 4~6학년부")
    [line] = duplicate_check_requests([(a, b)])
    assert line.startswith("서류 확인:")
    assert "여초등 1~3학년부 · 여초등 4~6학년부" in line
    assert line.count("가람.hwp") == 1
