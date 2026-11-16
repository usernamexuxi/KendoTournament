"""책자 앞쪽 두 쪽: 「대회식순·대회임원」과 「일정안내」. 틀은 참고 책자(광명시장기 카탈로그)를 따른다.

쪽 머리는 왼쪽 끝에서 나오는 남색 띠에 흰 제목, 띠 아래로 가는 선이 오른쪽 끝까지 이어진다.
식순은 「항목 ······ 맡은 사람」, 임원은 두 단, 경기장 배치는 남색 머리를 단 연분홍 칸이다.
"""

from __future__ import annotations

from kendo_tournament.domain.layout.bracket_style import NAVY, WHITE
from kendo_tournament.domain.layout.document_pages import wrap
from kendo_tournament.domain.layout.primitives import (
    MM_PER_PT,
    PAGE_WIDTH,
    Align,
    LineItem,
    PageLayout,
    RectItem,
    TextItem,
    estimated_width_mm,
)
from kendo_tournament.domain.program import ProgramContent, Row

MARGIN = 14.0
HEAD_WIDTH = 62.0
HEAD_HEIGHT = 11.0
HEAD_PT = 17.0
HEAD_RULE_PT = 1.2
BODY_PT = 9.5
SMALL_PT = 8.5
ROW = 6.2
INK_SOFT = "#4a4a4a"
COURT_FILL = "#f6eaf1"
PILL_WIDTH = 30.0
ITEM_WIDTH = 26.0
PERFORMER_WIDTH = 16.0
LABEL_WIDTH = 18.0
PILL_HEIGHT = 6.5
PILL_PT = 10.0
LEADER_START = 62.0
LEADER_END = 146.0
PERFORMER_X = 150.0
DOT_STEP = 1.3
DOT_LENGTH = 0.25
OFFICIAL_ROLE_WIDTH = 18.0
OFFICIAL_COLUMNS = (MARGIN, PAGE_WIDTH / 2 + 4)
OFFICIAL_NAME_WIDTH = PAGE_WIDTH / 2 - MARGIN - OFFICIAL_ROLE_WIDTH - 8
SUB_PT = 13.0
LABEL_X = 30.0
VALUE_X = 62.0
COURT_HEAD = 8.0
COURT_GAP = 6.0
NOTE_MARK = "●"


def _justified(page: PageLayout, text: str, x: float, y: float, width: float) -> None:
    """책자처럼 항목 이름을 정해진 폭에 고르게 편다(「개 회 식 통 보」·「축 　 사」의 끝이 맞는다).

    글자가 너무 많아 폭을 넘으면 펴지 않고 그대로 쓴다.
    """
    chars = list(text.replace(" ", ""))
    if len(chars) < 2 or estimated_width_mm(text, BODY_PT) >= width:
        page.texts.append(TextItem(x, y, text, BODY_PT, Align.LEFT, color=INK_SOFT))
        return
    char_width = estimated_width_mm(chars[0], BODY_PT)
    step = (width - char_width) / (len(chars) - 1)
    for index, char in enumerate(chars):
        page.texts.append(TextItem(x + index * step, y, char, BODY_PT, Align.LEFT, color=INK_SOFT))


def _wrap_names(names: str, width: float) -> list[str]:
    """이름 목록을 쉼표 단위로 줄바꿈한다. 글자 단위로 자르면 이름이 두 줄에 걸쳐 쪼개진다."""
    lines: list[str] = []
    current = ""
    for token in (part.strip() for part in names.split(",")):
        candidate = f"{current}, {token}" if current else token
        if current and estimated_width_mm(candidate, BODY_PT) > width:
            lines.append(current + ",")
            current = token
        else:
            current = candidate
    lines.append(current)
    return lines


def page_head(page: PageLayout, title: str, top: float) -> float:
    page.rects.append(RectItem(0.0, top, HEAD_WIDTH, HEAD_HEIGHT, NAVY))
    page.texts.append(TextItem(MARGIN, top + HEAD_HEIGHT / 2, title, HEAD_PT, Align.LEFT, bold=True, color=WHITE))
    bottom = top + HEAD_HEIGHT
    page.lines.append(LineItem(HEAD_WIDTH, bottom, PAGE_WIDTH, bottom, HEAD_RULE_PT))
    return bottom


def _pill(page: PageLayout, title: str, y: float) -> None:
    """가운데 남색 둥근 이름표(「개회식」)와 양옆으로 뻗는 선."""
    center = PAGE_WIDTH / 2
    left, right = center - PILL_WIDTH / 2, center + PILL_WIDTH / 2
    page.lines += [LineItem(LEADER_START - 22, y, left, y, 0.5), LineItem(right, y, PERFORMER_X + 30, y, 0.5)]
    page.rects.append(RectItem(left, y - PILL_HEIGHT / 2, PILL_WIDTH, PILL_HEIGHT, NAVY))
    page.texts.append(TextItem(center, y, title, PILL_PT, Align.CENTER, bold=True, color=WHITE))


def _leader(page: PageLayout, y: float) -> None:
    x = LEADER_START + 18
    while x < LEADER_END:
        page.lines.append(LineItem(x, y, x + DOT_LENGTH, y, 0.6))
        x += DOT_STEP


def _ceremony(page: PageLayout, title: str, rows: tuple[Row, ...], y: float) -> float:
    _pill(page, title, y)
    y += ROW * 1.4
    for item, performer in rows:
        _justified(page, item, LEADER_START - 22, y, ITEM_WIDTH)
        _leader(page, y + BODY_PT * MM_PER_PT * 0.3)
        if performer:
            _justified(page, performer, PERFORMER_X, y, PERFORMER_WIDTH)
        y += ROW
    return y + ROW * 0.6


def _official(page: PageLayout, x: float, y: float, row: Row) -> float:
    role, names = row
    _justified(page, role, x, y, OFFICIAL_ROLE_WIDTH)
    for line in _wrap_names(names, OFFICIAL_NAME_WIDTH):
        page.texts.append(TextItem(x + OFFICIAL_ROLE_WIDTH + 4, y, line, BODY_PT, Align.LEFT))
        y += ROW
    return y


def _officials(page: PageLayout, rows: tuple[Row, ...], y: float) -> float:
    half = (len(rows) + 1) // 2
    bottoms = []
    for x, column in zip(OFFICIAL_COLUMNS, (rows[:half], rows[half:]), strict=True):
        cursor = y
        for row in column:
            cursor = _official(page, x, cursor, row)
        bottoms.append(cursor)
    return max(bottoms)


def ceremony_page(content: ProgramContent) -> PageLayout:
    """「대회식순」(개회식·폐회식)과 「대회임원」을 한 쪽에."""
    page = PageLayout()
    y = page_head(page, "대회식순", 14.0) + 12
    y = _ceremony(page, "개회식", content.opening, y)
    if content.closing:
        y = _ceremony(page, "폐회식", content.closing, y + 4)
    y = page_head(page, "대회임원", y + 4) + 9
    _officials(page, content.officials, y)
    return page


def _sub(page: PageLayout, title: str, y: float) -> float:
    page.texts.append(TextItem(MARGIN + 10, y, title, SUB_PT, Align.LEFT, bold=True))
    page.lines.append(LineItem(MARGIN + 34, y + 1.5, PAGE_WIDTH - MARGIN - 10, y + 1.5, 0.8))
    return y + ROW * 1.6


def _labelled(page: PageLayout, rows: tuple[Row, ...], y: float) -> float:
    for label, value in rows:
        _justified(page, label, LABEL_X, y, LABEL_WIDTH)
        page.texts.append(TextItem(VALUE_X, y, value, BODY_PT, Align.LEFT))
        y += ROW
    return y


def _notes(page: PageLayout, notes: tuple[str, ...], y: float) -> float:
    width = PAGE_WIDTH - MARGIN - VALUE_X - 4
    for note in notes:
        page.texts.append(TextItem(VALUE_X, y, NOTE_MARK, SMALL_PT, Align.LEFT, color=INK_SOFT))
        for line in wrap(note, width, BODY_PT):
            page.texts.append(TextItem(VALUE_X + 4, y, line, BODY_PT, Align.LEFT))
            y += ROW
    return y


def _courts(page: PageLayout, courts: tuple[Row, ...], y: float) -> float:
    if not courts:
        return y
    total = PAGE_WIDTH - 2 * (MARGIN + 16)
    width = (total - COURT_GAP * (len(courts) - 1)) / len(courts)
    lists = [[part.strip() for part in divisions.split(",") if part.strip()] for _, divisions in courts]
    height = COURT_HEAD + (max(len(items) for items in lists) + 1) * ROW
    for index, ((name, _), items) in enumerate(zip(courts, lists, strict=True)):
        left = MARGIN + 16 + index * (width + COURT_GAP)
        page.rects.append(RectItem(left, y + COURT_HEAD, width, height - COURT_HEAD, COURT_FILL))
        page.rects.append(RectItem(left, y, width, COURT_HEAD, NAVY))
        page.texts.append(TextItem(left + width / 2, y + COURT_HEAD / 2, name, BODY_PT, Align.CENTER, bold=True, color=WHITE))
        for row, division in enumerate(items, start=1):
            text = TextItem(left + width / 2, y + COURT_HEAD + row * ROW, division, BODY_PT, Align.CENTER, max_width=width - 4)
            page.texts.append(text)
    return y + height + ROW


def _rules(page: PageLayout, rules: tuple[str, ...], y: float) -> float:
    for number, rule in enumerate(rules, start=1):
        page.texts.append(
            TextItem(LABEL_X, y, f"{number}.  {rule}", BODY_PT, Align.LEFT, max_width=PAGE_WIDTH - LABEL_X - MARGIN)
        )
        y += ROW
    return y


def schedule_page(content: ProgramContent) -> PageLayout:
    """「일정안내」: 경기 일정 · 경기 안내 · 경기장 배치 · 경기장 수칙."""
    page = PageLayout()
    y = page_head(page, "일정안내", 14.0) + 16
    y = _labelled(page, content.schedule, _sub(page, "경기 일정", y)) + ROW
    y = _labelled(page, content.match_guide, _sub(page, "경기 안내", y))
    y = _notes(page, content.guide_notes, y) + ROW
    y = _courts(page, content.courts, _sub(page, "경기장 배치", y)) + ROW
    _rules(page, content.court_rules, _sub(page, "경기장 수칙", y))
    return page


def program_pages(content: ProgramContent) -> list[PageLayout]:
    return [ceremony_page(content), schedule_page(content)]
