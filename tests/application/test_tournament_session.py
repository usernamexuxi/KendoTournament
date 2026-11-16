import pytest

from kendo_tournament.application.tournament_session import TournamentSession
from kendo_tournament.domain.model import DivisionRule, Entry, Event, Gender, Grade
from kendo_tournament.infrastructure.readers.registry import reader_for
from kendo_tournament.infrastructure.storage.json_repository import JsonTournamentRepository
from tests.infrastructure.fixtures import make_docx

RULES = [DivisionRule("r1", Event.INDIVIDUAL, Gender.MALE, Grade(1), Grade(6))]


def session(tmp_path):
    return TournamentSession(JsonTournamentRepository(), reader_for, tmp_path / "저장")


def rows(names, grade="초2"):
    return [(str(i), name, "남", grade, "") for i, name in enumerate(names)]


def test_바꿀때마다_자동저장되고_다시_열면_그대로다(tmp_path):
    s = session(tmp_path)
    s.new("광명시장배: 2026")
    s.import_files([make_docx(tmp_path / "a.docx", "가관", rows(["가가", "나나", "다다"]))])
    s.set_rules(RULES)
    s.draw_missing()
    label = s.tournament.divisions[0].label
    s.set_title(label, "남자 초등부 개인전")
    assert s.path.name == "광명시장배_ 2026.kendo"

    reopened = session(tmp_path)
    reopened.open(s.path)
    assert reopened.tournament == s.tournament


def test_같은_파일을_다시_넣으면_그_파일_명단을_바꾸고_대진은_지킨다(tmp_path):
    s = session(tmp_path)
    s.new("대회")
    path = make_docx(tmp_path / "a.docx", "가관", rows(["가가", "나나", "다다"]))
    s.import_files([path])
    s.set_rules(RULES)
    s.draw_missing()
    label = s.tournament.divisions[0].label
    before = s.bracket(label)

    make_docx(path, "가관", rows(["가가", "나나", "다다", "라라"]))
    s.import_files([path])
    s.refresh_divisions()
    assert len(s.tournament.participants) == 4
    assert s.bracket(label) == before
    added, removed = s.pending(label)
    assert [e.name for e in added] == ["라라"] and removed == []

    after = s.insert(label, added[0])
    assert len(after.entries) == 4
    assert s.pending(label) == ([], [])


def test_빈자리가_없으면_끼워넣기를_거절한다(tmp_path):
    s = session(tmp_path)
    s.new("대회")
    s.import_files([make_docx(tmp_path / "a.docx", "가관", rows(["가가", "나나"]))])
    s.set_rules(RULES)
    s.draw_missing()
    label = s.tournament.divisions[0].label
    with pytest.raises(ValueError, match="다시 추첨"):
        s.insert(label, Entry("x", "새사람", "나관"))


def test_출력_미리보기는_저장할_때와_같은_쪽을_돌려준다(tmp_path):
    class PageCatcher:
        pages = None

        def export(self, pages, path):
            PageCatcher.pages = pages

    s = session(tmp_path)
    s.new("대회")
    s.import_files([make_docx(tmp_path / "a.docx", "가관", rows(["가가", "나나", "다다"]))])
    s.set_rules(RULES)
    s.draw_missing()
    labels = [d.label for d in s.tournament.divisions]
    s.export(labels, PageCatcher(), tmp_path / "out.pdf")
    assert s.print_pages(labels) == PageCatcher.pages
    assert s.print_pages([]) == []


def test_나뉜_부문을_손으로_합치고_나누면_규칙에_남는다(tmp_path):
    s = session(tmp_path)
    s.new("대회")
    s.import_files([make_docx(tmp_path / "a.docx", "가관", rows(["가가", "나나"], "초1") + rows(["다다", "라라"], "초2"))])
    per_grade = [DivisionRule(f"r{g}", Event.INDIVIDUAL, Gender.MALE, Grade(g), Grade(g)) for g in (1, 2)]
    s.set_rules(per_grade)
    assert [d.label for d in s.tournament.divisions] == ["남자 초1 개인전", "남자 초2 개인전"]

    s.merge_divisions(["남자 초1 개인전", "남자 초2 개인전"])
    assert [d.label for d in s.tournament.divisions] == ["남자 초1~초2 개인전"]
    s.refresh_divisions()
    assert [d.label for d in s.tournament.divisions] == ["남자 초1~초2 개인전"]

    s.split_divisions(["남자 초1~초2 개인전"])
    assert [d.label for d in s.tournament.divisions] == ["남자 초1 개인전", "남자 초2 개인전"]


def test_부전승_추천_여러_건을_한_번에_합치면_묶음마다_따로_합쳐진다(tmp_path):
    from kendo_tournament.domain.model import DivisionRule, Event, Gender, Grade, Participant

    s = TournamentSession(JsonTournamentRepository(), reader_for, tmp_path)
    s.new("부전승")
    people = [
        Participant(f"{grade}-{i}", f"선수{grade}{i}", Gender.FEMALE, f"관{i}", grade=Grade(grade))
        for grade, count in ((7, 5), (8, 7), (10, 3), (11, 3))
        for i in range(count)
    ]
    s.set_participants(people)
    rules = [DivisionRule(f"f{g}", Event.INDIVIDUAL, Gender.FEMALE, Grade(g), Grade(g)) for g in (7, 8, 10, 11)]
    result = s.set_rules(rules)
    groups = [list(advice.labels) for advice in result.byes.merges]
    assert len(groups) == 2
    after = s.merge_division_groups(groups)
    assert sorted(len(d.entries) for d in after.divisions) == [6, 12]


def test_신청서에_학년이_범위로만_적힌_부문은_학년별로_나누지_않는다(tmp_path):
    from kendo_tournament.domain.model import Participant

    s = session(tmp_path)
    s.new("대회")
    s.tournament.participants = [
        Participant(pid, f"선수{pid}", Gender.MALE, f"도장{pid}", Grade(1), category="남초등 1~2학년") for pid in "abc"
    ]
    s.set_rules([DivisionRule("r1", Event.INDIVIDUAL, Gender.MALE, Grade(1), Grade(2))])
    with pytest.raises(ValueError, match="학년별로 나눌 수 없습니다"):
        s.split_divisions(["남자 초1~초2 개인전"])
    assert [d.label for d in s.tournament.divisions] == ["남자 초1~초2 개인전"]


def test_알아볼_수_없는_종별이_든_표는_저장하지_않는다(tmp_path):
    from kendo_tournament.domain.division.category_table import DEFAULT_CATEGORY_TABLE, CategoryTable

    s = session(tmp_path)
    s.new("대회")
    with pytest.raises(ValueError, match="26명 참가"):
        s.set_categories(CategoryTable(("남초등 1~2학년", "26명 참가"), ()))
    assert s.tournament.categories == DEFAULT_CATEGORY_TABLE


def test_신청서_양식이_없는_파일에서는_종별을_못_읽는다고_알린다(tmp_path):
    s = session(tmp_path)
    path = make_docx(tmp_path / "a.docx", "가관", rows(["가가"]))
    with pytest.raises(ValueError, match="찾지 못했습니다"):
        s.categories_in_file(path)


def test_직접_적은_신청서는_명단에_들어가고_같은_도장을_다시_적으면_그_명단만_바뀐다(tmp_path):
    from kendo_tournament.domain.written_form import IndividualLine, TeamLine, WrittenForm

    s = session(tmp_path)
    s.import_files([make_docx(tmp_path / "가람.docx", "가람검도관", rows(["김하나"]))])
    first = WrittenForm(
        "누리검도관",
        (IndividualLine("남초등 1~2학년", ("이두리", "박세찬")),),
        (TeamLine("초등고학년 4~6학년", "A", (("선봉", "오가온"), ("주장", "윤마루"))),),
    )
    s.add_written_form(first)
    names = sorted(p.name for p in s.tournament.participants)
    assert names == ["김하나", "박세찬", "오가온", "윤마루", "이두리"]
    assert [t.name for t in s.tournament.teams] == ["누리검도관 A"]
    s.add_written_form(WrittenForm("누리검도관", (IndividualLine("남초등 1~2학년", ("이두리",)),), ()))
    assert sorted(p.name for p in s.tournament.participants) == ["김하나", "이두리"]
    assert s.tournament.teams == []
