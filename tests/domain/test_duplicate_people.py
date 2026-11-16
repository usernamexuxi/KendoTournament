"""명단의 「중복 의심」. 실제 신청서는 같은 사람을 개인전 표와 단체전 표에 함께 적는다 — 그건 중복이 아니다."""

from kendo_tournament.domain.model import Gender, Participant, Team
from kendo_tournament.domain.tournament import Tournament


def person(pid, name="김하나", dojang="가람검도관"):
    return Participant(pid, name, Gender.MALE, dojang, source="가람.hwp")


def test_같은_사람이_개인전과_단체전에_함께_있으면_중복_의심이_아니다():
    t = Tournament("대회")
    t.participants = [person("개인"), person("팀원")]
    t.teams = [Team("팀", "가람검도관 A", "가람검도관", ("팀원",))]
    assert t.duplicate_people() == []


def test_개인전에_같은_도장_같은_이름이_두_번이면_중복_의심이다():
    t = Tournament("대회")
    t.participants = [person("a"), person("b")]
    assert [(a.id, b.id) for a, b in t.duplicate_people()] == [("a", "b")]


def test_두_팀에_같은_도장_같은_이름이_있으면_중복_의심이다():
    t = Tournament("대회")
    t.participants = [person("a"), person("b")]
    t.teams = [Team("A", "가람검도관 A", "가람검도관", ("a",)), Team("B", "가람검도관 B", "가람검도관", ("b",))]
    assert len(t.duplicate_people()) == 1


def test_한_신청서가_같은_이름을_두_종별에_적었으면_작성_실수로_의심한다():
    t = Tournament("대회")
    t.participants = [
        Participant("a", "김하나", Gender.FEMALE, "가람검도관", source="가람.hwp", category="여초등 1~3학년부"),
        Participant("b", "김하나", Gender.FEMALE, "가람검도관", source="가람.hwp", category="여초등 4~6학년부"),
    ]
    assert len(t.duplicate_people()) == 1


def test_두_신청서에_같은_도장_같은_이름이_있으면_종별이_달라도_중복_의심이다():
    t = Tournament("대회")
    t.participants = [
        Participant("a", "김하나", Gender.FEMALE, "가람검도관", source="가람.hwp", category="여초등 1~3학년부"),
        Participant("b", "김하나", Gender.FEMALE, "가람검도관", source="가람(수정).hwp", category="여초등 4~6학년부"),
    ]
    assert len(t.duplicate_people()) == 1
