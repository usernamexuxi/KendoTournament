from pathlib import Path

from kendo_tournament.application.draw_brackets import draw_all, rebuild_divisions
from kendo_tournament.application.export_brackets import export_pages, pages_for
from kendo_tournament.application.import_roster import import_roster
from kendo_tournament.domain.draw.validate import first_match_conflicts
from kendo_tournament.domain.model import DivisionRule, Event, Gender, Grade
from kendo_tournament.domain.tournament import Tournament
from kendo_tournament.infrastructure.exporters.pdf_exporter import PdfExporter
from kendo_tournament.infrastructure.readers.registry import reader_for
from tests.infrastructure.fixtures import make_docx

GIVEN = "김이박최정강조윤장임"
FAMILY = "민서준하도윤지우현수"


def fake_rows(prefix, count, gender, grade):
    return [(str(i), f"{GIVEN[i % 10]}{FAMILY[(i + len(prefix)) % 10]}{prefix}{i}", gender, grade, "") for i in range(count)]


def test_워드_신청서_세장으로_대진표_PDF까지(tmp_path: Path):
    files = [
        make_docx(tmp_path / "가.docx", "광명검도관", fake_rows("가", 6, "남", "초3") + fake_rows("가", 2, "여", "초3")),
        make_docx(tmp_path / "나.docx", "하안 검도장", fake_rows("나", 5, "남", "초4")),
        make_docx(tmp_path / "다.docx", "철산검도관", fake_rows("다", 4, "남", "초3") + fake_rows("다", 1, "남", "중1")),
    ]
    report = import_roster(files + [tmp_path / "옛날.doc"], reader_for)
    assert len(report.participants) == 18
    assert report.problems == ()
    assert len(report.rejected) == 1

    tournament = Tournament("시험 대회")
    tournament.participants = list(report.participants)
    tournament.rules = [
        DivisionRule("m34", Event.INDIVIDUAL, Gender.MALE, Grade(3), Grade(4)),
        DivisionRule("f3", Event.INDIVIDUAL, Gender.FEMALE, Grade(3), Grade(3), min_entries=4),
        DivisionRule("m7", Event.INDIVIDUAL, Gender.MALE, Grade(7), Grade(9)),
    ]
    result = rebuild_divisions(tournament)
    assert [d.label for d in tournament.divisions] == ["남자 초3~초4 개인전", "여자 초3 개인전", "남자 중1~중3 개인전"]
    assert "합칠 종별이 없습니다" in result.warnings[0]

    brackets = draw_all(tournament)
    male = brackets[0]
    assert first_match_conflicts(male, tournament.dojang_of) == []
    assert len(first_match_conflicts(brackets[1], tournament.dojang_of)) == 1, "한 도장 두 명뿐인 부문은 피할 수 없다"

    pages = pages_for(brackets)
    output = export_pages(pages, PdfExporter(), tmp_path / "대진표.pdf")
    assert output.read_bytes()[:4] == b"%PDF"
