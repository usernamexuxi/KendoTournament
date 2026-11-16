from kendo_tournament.domain.division.builder import build_divisions
from kendo_tournament.domain.division.category_table import GWANGMYEONG_MAYOR, TEMPLATES, CategoryTable
from kendo_tournament.domain.division.presets import PresetChoice, make_rules
from kendo_tournament.domain.model import Event, Gender, Grade, Participant


def test_모든_틀의_종별은_성별_학년을_알아볼_수_있다():
    assert all(table.unreadable() == [] for table in TEMPLATES.values())


def test_알아볼_수_없는_종별을_찾는다():
    assert CategoryTable(("남초등 1~2학년", "26명 참가"), ()).unreadable() == ["26명 참가"]


def test_시장기_틀이면_남초_개인전이_학년마다_생긴다():
    choice = PresetChoice((Event.INDIVIDUAL,), categories=GWANGMYEONG_MAYOR)
    labels = [rule.label for rule in make_rules(choice)]
    assert labels[:6] == [f"남자 초{grade} 개인전" for grade in range(1, 7)]
    assert "남자 중1~중3 개인전" in labels and "남자 고1~고3 개인전" in labels


def test_시장기_신청서_학년_선수는_자기_학년_부문에_든다():
    people = [Participant(pid, f"선수{pid}", Gender.MALE, f"도장{pid}", Grade(2), category="남초등 2학년") for pid in "ab"]
    choice = PresetChoice((Event.INDIVIDUAL,), categories=GWANGMYEONG_MAYOR)
    result = build_divisions(people, [], make_rules(choice, participants=people))
    assert [(d.label, len(d.entries)) for d in result.divisions] == [("남자 초2 개인전", 2)]
