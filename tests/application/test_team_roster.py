from kendo_tournament.application.team_roster import member_line
from kendo_tournament.domain.model import Participant, Team


def people(*names):
    return {f"p{i}": Participant(f"p{i}", name, None, "도장") for i, name in enumerate(names)}


def test_자리가_있으면_자리와_이름을_쓰고_후보는_맨_끝이다():
    named = people("서다인", "오가온", "윤마루")
    team = Team("t", "도장 A", "도장", ("p0", "p1", "p2"), positions=("후보", "선봉", "주장"))
    assert member_line(team, {pid: p.name for pid, p in named.items()}) == "선봉 오가온 · 주장 윤마루 · 후보 서다인"


def test_자리가_없는_예전_팀은_이름만_쓴다():
    named = people("오가온", "윤마루")
    team = Team("t", "도장 A", "도장", ("p0", "p1"))
    assert member_line(team, {pid: p.name for pid, p in named.items()}) == "오가온 · 윤마루"
