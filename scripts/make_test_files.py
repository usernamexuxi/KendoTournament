"""프로그램을 손으로 시험해 볼 가짜 신청서를 test_file/광명 (광명 대회)·test_file/전국 (전국 대회) 에 만든다.

이름·주소·연락처는 전부 지어낸 것이다. 실행: .venv/Scripts/python.exe scripts/make_test_files.py

양식은 실제 광명시 회장기 신청서를 따른다(application_form.py). 전국 대회도 같은 양식을 쓰고,
도장의 시·도는 주소 칸에만 나온다(실제 양식에 지역 칸이 없다).

한글 바이너리(.hwp)는 한글 프로그램 없이는 만들 수 없어 한글 파일은 .hwpx 로 만든다.
여기서 만든 .hwpx 는 이 프로그램의 리더가 읽는 최소 구조(본문 XML)만 갖고 있어서,
한글 프로그램에서 열리는지는 보장하지 않는다 — 프로그램 시험용이다.
"""

from __future__ import annotations

import random
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

from application_form import (
    INDIVIDUAL_CATEGORIES,
    POSITIONS,
    TEAM_CATEGORIES,
    TEAM_LETTERS,
    Applicant,
    Contest,
    Page,
    Rows,
    TeamMember,
    form_pages,
)
from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUTPUT = Path(__file__).resolve().parent.parent / "test_file"
FAMILY = "김이박최정강조윤장임한오서신권황안송류홍"
GIVEN = (
    "민준", "서준", "도윤", "예준", "시우", "하준", "지호", "주원", "지우", "서연",
    "서윤", "지민", "하은", "수아", "지아", "채원", "다은", "예린", "유나", "소율",
    "건우", "우진", "선우", "연우", "유준", "정우", "승우", "승현", "시윤", "준혁",
    "은우", "지환", "승민", "지훈", "유찬", "윤우", "민성", "준영", "시후", "진우",
    "윤서", "민서", "하윤", "지유", "서현", "예은", "수빈", "지원", "소윤", "채은",
)  # fmt: skip
TOURNAMENT_YEAR = 2026
SIGNED_ON = f"{TOURNAMENT_YEAR}.    11.    06."
# 개인전 종별마다 뽑힐 비중. 초등부가 가장 많고 성인부가 적은 실제 신청서 모양을 흉내 낸다.
CATEGORY_WEIGHTS = (6, 6, 6, 4, 4, 2, 4, 3, 2, 2, 1, 1)
TEAM_COUNT_CHOICES = (1, 1, 2)
MAX_TEAM_CATEGORIES = 3
SUBSTITUTE_SHARE = 0.3
# 단체전 종별 → 팀원 학년 범위(초1=1 … 고3=12). None 은 일반부(태어난 해로 정한다).
TEAM_GRADES = {
    "초등저학년 1~3학년": (1, 3),
    "초등고학년 4~6학년": (4, 6),
    "여청소년부(중,고)": (7, 12),
    "남청소년부(중,고)": (7, 12),
    "남자일반부": None,
}
ADULT_BIRTH_YEARS = (1975, 2005)
FIRST_SCHOOL_AGE = 8
SEED = 2026
FONT_NAME = "MalgunTest"
FONT_FILE = Path(r"C:\Windows\Fonts\malgun.ttf")


@dataclass(frozen=True)
class Dojang:
    """도장 이름은 동네 이름 + 검도관으로 서로 겹치지 않게 짓는다(개발자 지시). region 은 시·도.

    enters_teams 가 거짓이면 단체전 쪽을 종별도 안 고른 빈 쪽으로 낸다 — 실제로 그렇게 오는 신청서가 있다.
    """

    area: str
    size: int
    file_format: str
    region: str = "경기도 광명시"
    enters_teams: bool = True

    @property
    def name(self) -> str:
        return f"{self.area}검도관"


@dataclass(frozen=True)
class ContestFiles:
    folder: str
    contest: Contest
    dojangs: tuple[Dojang, ...]


CONTESTS = (
    ContestFiles(
        "광명",
        Contest(f"{TOURNAMENT_YEAR} 광명시장배 검도대회", SIGNED_ON, "광명시검도회장"),
        (
            Dojang("철산", 28, "hwpx"),
            Dojang("하안", 24, "hwpx"),
            Dojang("소하", 22, "hwpx"),
            Dojang("일직", 18, "hwpx", enters_teams=False),
            Dojang("광명", 20, "hwpx"),
            Dojang("학온", 15, "hwpx"),
            Dojang("옥길", 19, "docx"),
            Dojang("가학", 16, "pdf"),
        ),
    ),
    ContestFiles(
        "전국",
        Contest(f"{TOURNAMENT_YEAR} 전국 학생·일반 검도대회", SIGNED_ON, "대회장"),
        (
            Dojang("강남", 26, "hwpx", "서울특별시 강남구"),
            Dojang("마포", 21, "hwpx", "서울특별시 마포구"),
            Dojang("해운대", 24, "hwpx", "부산광역시 해운대구"),
            Dojang("수성", 19, "hwpx", "대구광역시 수성구"),
            Dojang("송도", 17, "hwpx", "인천광역시 연수구"),
            Dojang("상무", 15, "hwpx", "광주광역시 서구", enters_teams=False),
            Dojang("유성", 18, "hwpx", "대전광역시 유성구"),
            Dojang("영통", 22, "hwpx", "경기도 수원시"),
            Dojang("효자", 14, "hwpx", "강원특별자치도 춘천시"),
            Dojang("노형", 16, "docx", "제주특별자치도 제주시"),
            Dojang("완산", 20, "pdf", "전북특별자치도 전주시"),
        ),
    ),
)


def _unique_name(rng: random.Random, used: set[str]) -> str:
    """대회 하나 안에서 겹치지 않는 이름. 겹치면 프로그램이 「중복 의심」을 띄워 시험이 흐려진다."""
    while True:
        name = rng.choice(FAMILY) + rng.choice(GIVEN)
        if name not in used:
            used.add(name)
            return name


def _birth(rng: random.Random, grades: tuple[int, int] | None) -> str:
    """신청서 단체전 표의 생년월일(YYMMDD)."""
    if grades is None:
        year = rng.randint(*ADULT_BIRTH_YEARS)
    else:
        year = TOURNAMENT_YEAR - (rng.randint(*grades) + FIRST_SCHOOL_AGE - 1)
    return f"{year % 100:02d}{rng.randint(1, 12):02d}{rng.randint(1, 28):02d}"


def _individuals(rng: random.Random, size: int, used: set[str]) -> dict[str, list[str]]:
    individuals: dict[str, list[str]] = {}
    for category in rng.choices(INDIVIDUAL_CATEGORIES, weights=CATEGORY_WEIGHTS, k=size):
        individuals.setdefault(category, []).append(_unique_name(rng, used))
    return individuals


def _teams(rng: random.Random, used: set[str]) -> dict[str, list[list[TeamMember]]]:
    teams: dict[str, list[list[TeamMember]]] = {}
    chosen = rng.sample(TEAM_CATEGORIES, rng.randint(1, MAX_TEAM_CATEGORIES))
    for category in TEAM_CATEGORIES:
        if category not in chosen:
            continue
        for _ in range(min(rng.choice(TEAM_COUNT_CHOICES), len(TEAM_LETTERS))):
            size = len(POSITIONS) if rng.random() < SUBSTITUTE_SHARE else len(POSITIONS) - 1
            members = [TeamMember(_unique_name(rng, used), _birth(rng, TEAM_GRADES[category])) for _ in range(size)]
            teams.setdefault(category, []).append(members)
    return teams


def make_applicant(rng: random.Random, dojang: Dojang, used: set[str]) -> Applicant:
    return Applicant(
        dojang=dojang.name,
        address=f"{dojang.region} {dojang.area}로 {rng.randint(1, 300)}",
        head=_unique_name(rng, used),
        phone=f"010-0000-{rng.randint(0, 9999):04d}",
        individuals=_individuals(rng, dojang.size, used),
        teams=_teams(rng, used) if dojang.enters_teams else {},
    )


def _hwpx_paragraph(text: str) -> str:
    return f"<hp:p><hp:run><hp:t>{escape(text)}</hp:t></hp:run></hp:p>"


def _hwpx_table(rows: Rows) -> str:
    cell = "<hp:tc><hp:subList><hp:p><hp:run><hp:t>{}</hp:t></hp:run></hp:p></hp:subList></hp:tc>"
    body = "".join("<hp:tr>" + "".join(cell.format(escape(text)) for text in row) + "</hp:tr>" for row in rows)
    return f"<hp:p><hp:run><hp:tbl>{body}</hp:tbl></hp:run></hp:p>"


def write_hwpx(path: Path, pages: list[Page]) -> None:
    namespaces = 'xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"'
    parts = [_hwpx_paragraph(block) if isinstance(block, str) else _hwpx_table(block) for page in pages for block in page]
    section = f'<?xml version="1.0" encoding="UTF-8"?><hs:sec {namespaces}>{"".join(parts)}</hs:sec>'
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", "application/hwp+zip", compress_type=zipfile.ZIP_STORED)
        archive.writestr("Contents/section0.xml", section, compress_type=zipfile.ZIP_DEFLATED)


def _docx_table(document, rows: Rows) -> None:
    table = document.add_table(rows=0, cols=len(rows[0]))
    table.style = "Table Grid"
    for row in rows:
        for cell, text in zip(table.add_row().cells, row, strict=True):
            cell.text = text


def write_docx(path: Path, pages: list[Page]) -> None:
    document = Document()
    for page_no, page in enumerate(pages):
        if page_no:
            document.add_page_break()
        for block in page:
            if isinstance(block, str):
                document.add_paragraph(block)
            else:
                _docx_table(document, block)
    document.save(str(path))


def write_pdf(path: Path, pages: list[Page]) -> None:
    if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_FILE)))
    style = ParagraphStyle("body", fontName=FONT_NAME, fontSize=10, leading=15)
    grid = TableStyle(
        [("FONTNAME", (0, 0), (-1, -1), FONT_NAME), ("FONTSIZE", (0, 0), (-1, -1), 8), ("GRID", (0, 0), (-1, -1), 0.5, "black")]
    )
    story = []
    for page_no, page in enumerate(pages):
        if page_no:
            story.append(PageBreak())
        for block in page:
            if isinstance(block, str):
                story.append(Paragraph(escape(block), style))
                continue
            table = Table([list(row) for row in block])
            table.setStyle(grid)
            story += [Spacer(1, 6), table, Spacer(1, 6)]
    SimpleDocTemplate(str(path), pagesize=A4).build(story)


WRITERS = {"hwpx": write_hwpx, "docx": write_docx, "pdf": write_pdf}


def main() -> None:
    rng = random.Random(SEED)
    for files in CONTESTS:
        folder = OUTPUT / files.folder
        folder.mkdir(parents=True, exist_ok=True)
        for old in folder.glob("신청서_*"):
            old.unlink()
        used: set[str] = set()
        for dojang in files.dojangs:
            path = folder / f"신청서_{dojang.name}.{dojang.file_format}"
            WRITERS[dojang.file_format](path, form_pages(files.contest, make_applicant(rng, dojang, used)))
            print(path.relative_to(OUTPUT))


if __name__ == "__main__":
    main()
