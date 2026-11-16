import struct
import zipfile

import pytest
from docx import Document

from kendo_tournament.domain.model import Gender
from kendo_tournament.domain.ports import UnsupportedFormat
from kendo_tournament.infrastructure.readers.document_text import Paragraph, Table, blocks_to_result
from kendo_tournament.infrastructure.readers.hwp_reader import (
    TABLE_CTRL_ID,
    TAG_CTRL_HEADER,
    TAG_LIST_HEADER,
    TAG_PARA_TEXT,
    TAG_TABLE,
    para_text,
    parse_records,
    section_blocks,
)
from kendo_tournament.infrastructure.readers.registry import reader_for
from tests.infrastructure.fixtures import make_docx


def test_워드_신청서를_읽는다(tmp_path):
    path = make_docx(tmp_path / "a.docx", "광명검도관", [("1", "가나다", "남", "초3", ""), ("2", "라마바", "여", "", "15")])
    result = reader_for(path).read(path)
    assert [(p.name, p.gender, p.dojang) for p in result.participants] == [
        ("가나다", Gender.MALE, "광명검도관"),
        ("라마바", Gender.FEMALE, "광명검도관"),
    ]
    assert result.participants[0].grade.label == "초3"
    assert result.participants[1].age == 15
    assert result.problems == ()


def test_도장명이_표_안_칸에_있어도_읽는다(tmp_path):
    document = Document()
    table = document.add_table(rows=3, cols=3)
    for cell, text in zip(table.rows[0].cells, ("도장명", "하늘검도관", ""), strict=True):
        cell.text = text
    for cell, text in zip(table.rows[1].cells, ("이름", "성별", "학년"), strict=True):
        cell.text = text
    for cell, text in zip(table.rows[2].cells, ("가나다", "남자", "중1"), strict=True):
        cell.text = text
    path = tmp_path / "b.docx"
    document.save(str(path))
    result = reader_for(path).read(path)
    assert result.participants[0].dojang == "하늘검도관"


def test_빠진_칸은_문제로_알린다(tmp_path):
    path = make_docx(tmp_path / "c.docx", "광명검도관", [("1", "가나다", "", "3학년", "")])
    problems = reader_for(path).read(path).problems
    assert any("성별" in p for p in problems)
    assert any("3학년" in p for p in problems)


def test_이름_머리글이_없으면_읽지_못함으로_알린다(tmp_path):
    path = make_docx(tmp_path / "d.docx", "광명검도관", [("1", "x")], header=("번호", "비고"))
    result = reader_for(path).read(path)
    assert result.participants == ()
    assert "찾지 못했습니다" in result.problems[0]


def test_단체전_팀을_모은다():
    rows = (("이름", "성별", "학년", "팀"), ("가", "남", "성인", "A"), ("나", "남", "성인", "A"), ("다", "남", "성인", "B"))
    result = blocks_to_result([Paragraph("소속: 바다검도관"), Table(rows)], "e.hwpx")
    assert sorted((t.name, len(t.member_ids)) for t in result.teams) == [("바다검도관 A", 2), ("바다검도관 B", 1)]


@pytest.mark.parametrize("name", ["a.doc", "a.xlsx", "a.txt", "a"])
def test_허용목록에_없는_형식은_거부한다(tmp_path, name):
    with pytest.raises(UnsupportedFormat):
        reader_for(tmp_path / name)


def test_doc는_docx로_다시_저장하라고_안내한다(tmp_path):
    with pytest.raises(UnsupportedFormat, match=r"\.docx"):
        reader_for(tmp_path / "old.doc")


def _hwpx(path, section_xml):
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", "application/hwp+zip")
        archive.writestr("Contents/section0.xml", section_xml)
    return path


def test_hwpx_신청서를_읽는다(tmp_path):
    ns = 'xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"'

    def cell(text):
        return f"<hp:tc><hp:subList><hp:p><hp:run><hp:t>{text}</hp:t></hp:run></hp:p></hp:subList></hp:tc>"

    rows = [("이름", "성별", "학년"), ("가나다", "남", "고2")]
    table = "<hp:tbl>" + "".join("<hp:tr>" + "".join(cell(c) for c in r) + "</hp:tr>" for r in rows) + "</hp:tbl>"
    xml = (
        f"<hs:sec {ns}><hp:p><hp:run><hp:t>도장명: 별빛검도관</hp:t></hp:run></hp:p>"
        f"<hp:p><hp:run>{table}</hp:run></hp:p></hs:sec>"
    )
    path = _hwpx(tmp_path / "f.hwpx", xml)
    result = reader_for(path).read(path)
    assert [(p.name, p.dojang, p.grade.label) for p in result.participants] == [("가나다", "별빛검도관", "고2")]


def _record(tag, level, data):
    return struct.pack("<I", tag | (level << 10) | (len(data) << 20)) + data


def _utf16(text):
    return text.encode("utf-16-le")


def _cell_header(row, col):
    return struct.pack("<HHI", 1, 0, 0) + struct.pack("<HHHH", col, row, 1, 1)


def test_hwp_레코드에서_문단과_표를_꺼낸다():
    table_rows = [("이름", "성별", "나이"), ("가나다", "여", "12")]
    stream = _record(TAG_PARA_TEXT, 1, _utf16("도장명: 구름검도관"))
    stream += _record(TAG_CTRL_HEADER, 1, TABLE_CTRL_ID + b"\x00" * 4)
    stream += _record(TAG_TABLE, 2, struct.pack("<IHH", 0, 2, 3))
    for r, row in enumerate(table_rows):
        for c, text in enumerate(row):
            stream += _record(TAG_LIST_HEADER, 2, _cell_header(r, c))
            stream += _record(TAG_PARA_TEXT, 3, _utf16(text))
    blocks = list(section_blocks(parse_records(stream)))
    assert blocks[0] == Paragraph("도장명: 구름검도관")
    assert blocks[1] == Table((("이름", "성별", "나이"), ("가나다", "여", "12")))
    result = blocks_to_result(blocks, "g.hwp")
    assert result.participants[0].dojang == "구름검도관"
    assert result.participants[0].age == 12


def test_hwp_컨트롤_문자를_걷어낸다():
    wide = struct.pack("<H", 11) + b"\x00" * 14
    assert para_text(_utf16("가") + wide + _utf16("나") + struct.pack("<H", 13)) == "가나"


def _pdf_with_table(path, rows, with_text=True):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph as RLParagraph
    from reportlab.platypus import SimpleDocTemplate, TableStyle
    from reportlab.platypus import Table as RLTable

    from kendo_tournament.infrastructure.exporters.fonts import require_fonts

    regular, _, _ = require_fonts()
    pdfmetrics.registerFont(TTFont("TestKorean", str(regular)))
    story = []
    if with_text:
        story.append(RLParagraph("도장명: 달빛검도관", ParagraphStyle("p", fontName="TestKorean")))
        table = RLTable(rows)
        table.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), "TestKorean"), ("GRID", (0, 0), (-1, -1), 0.5, "black")]))
        story.append(table)
    else:
        story.append(RLTable([[""]]))
    SimpleDocTemplate(str(path), pagesize=A4).build(story)
    return path


def test_PDF_신청서를_읽는다(tmp_path):
    path = _pdf_with_table(tmp_path / "h.pdf", [["이름", "성별", "학년"], ["가나다", "남", "초5"]])
    result = reader_for(path).read(path)
    assert [(p.name, p.dojang, p.grade.label) for p in result.participants] == [("가나다", "달빛검도관", "초5")]


def test_글자없는_PDF는_스캔본으로_알린다(tmp_path):
    path = _pdf_with_table(tmp_path / "i.pdf", [], with_text=False)
    result = reader_for(path).read(path)
    assert result.participants == () and "스캔" in result.problems[0]


def test_도장_정보가_따로_된_표에_있어도_명단에_붙인다():
    info = (("도장명", "옥길검도관", "관장", "가나다"), ("주소", "경기도 광명시 옥길동", "연락처", "010-0000-0000"))
    roster = (
        ("번호", "성명", "성별", "생년월일", "학교", "학년", "단·급", "단체전", "비고"),
        ("1", "가가", "남", "2016.03.02", "옥길초등학교", "3", "1급", "", ""),
        ("2", "나나", "여", "2012.07.11", "옥길중학교", "1", "1단", "A팀", ""),
        ("3", "다다", "남", "1990.01.05", "", "일반", "3단", "A팀", "학부모"),
    )
    result = blocks_to_result([Paragraph("2026 광명시장배 검도대회 참가신청서"), Table(info), Table(roster)], "f.hwpx")
    assert result.problems == ()
    assert {p.dojang for p in result.participants} == {"옥길검도관"}
    assert [p.grade.label for p in result.participants] == ["초3", "중1", "성인"]
    assert [(t.name, len(t.member_ids)) for t in result.teams] == [("옥길검도관 A팀", 2)]
