"""「대회사」 쪽: 참고 책자(제26회 광명시장기 카탈로그 2쪽) 모양.

남색 띠 제목 아래 왼쪽에 사진, 첫 문단은 사진 오른쪽에 사진 아래 끝에 맞춰 붙고, 나머지 문단은 사진 아래로
폭 가득 이어진다. 오른쪽 아래에 날짜 · 직함 · 이름(크게, 글자 사이를 띄워)을 오른쪽 끝에 맞춰 둔다.
"""

from __future__ import annotations

from kendo_tournament.domain.greeting import Greeting, Photo
from kendo_tournament.domain.layout.document_pages import wrap
from kendo_tournament.domain.layout.primitives import PAGE_WIDTH, Align, ImageItem, PageLayout, TextItem
from kendo_tournament.domain.layout.program_pages import page_head

TITLE = "대회사"
HEAD_TOP = 22.0
TEXT_LEFT = 32.0
TEXT_RIGHT = PAGE_WIDTH - 32.0
PHOTO_TOP = 44.0
PHOTO_BOX_WIDTH, PHOTO_BOX_HEIGHT = 30.0, 37.0
PHOTO_GAP = 6.0
BODY_PT = 10.0
LINE = 6.6
PARAGRAPH_GAP = 5.0
INDENT = "  "
SIGN_RIGHT = PAGE_WIDTH - 42.0
DATE_Y = 246.0
POSITION_Y = 254.0
NAME_Y = 264.0
SIGN_PT = 10.0
NAME_PT = 15.0


def _photo_size(photo: Photo) -> tuple[float, float]:
    """사진 칸(가로 30 · 세로 37mm) 안에 비율을 지켜 가장 크게."""
    width = min(PHOTO_BOX_WIDTH, PHOTO_BOX_HEIGHT * photo.aspect)
    return width, width / photo.aspect


def _lines(page: PageLayout, lines: list[str], left: float, top: float) -> float:
    """줄들을 top 부터 쌓고 다음 줄 높이를 돌려준다. 높이는 글줄 가운데다."""
    y = top
    for line in lines:
        page.texts.append(TextItem(left, y, line, BODY_PT, Align.LEFT))
        y += LINE
    return y


def _body(page: PageLayout, paragraphs: list[str], photo: Photo | None) -> None:
    full = TEXT_RIGHT - TEXT_LEFT
    y = PHOTO_TOP + LINE / 2
    rest = paragraphs
    if photo is not None:
        width, height = _photo_size(photo)
        page.images.append(ImageItem(TEXT_LEFT, PHOTO_TOP, width, height, photo.png))
        y = PHOTO_TOP + height + LINE / 2 + PARAGRAPH_GAP
    if photo is not None and paragraphs:
        beside_left = TEXT_LEFT + width + PHOTO_GAP
        first = wrap(INDENT + paragraphs[0], TEXT_RIGHT - beside_left, BODY_PT)
        # 첫 문단의 마지막 줄이 사진 아래 끝에 오게 위로 쌓는다(책자처럼 사진 옆 아래쪽에 붙는다).
        top = max(PHOTO_TOP + LINE / 2, PHOTO_TOP + height - LINE / 2 - (len(first) - 1) * LINE)
        y = max(_lines(page, first, beside_left, top), PHOTO_TOP + height + LINE / 2) + PARAGRAPH_GAP
        rest = paragraphs[1:]
    for paragraph in rest:
        y = _lines(page, wrap(INDENT + paragraph, full, BODY_PT), TEXT_LEFT, y) + PARAGRAPH_GAP


def _spaced(name: str) -> str:
    """책자처럼 이름 글자 사이를 띄운다(「이 중 형」)."""
    return " ".join(name.replace(" ", ""))


def greeting_page(greeting: Greeting, date_text: str, photo: Photo | None) -> PageLayout:
    """date_text 는 오른쪽 아래에 찍을 날짜(대회사에 적은 날짜가 없으면 부르는 쪽이 대회 날짜를 넣는다)."""
    page = PageLayout()
    page_head(page, TITLE, HEAD_TOP)
    _body(page, greeting.paragraphs(), photo)
    signature = (
        (DATE_Y, date_text, SIGN_PT),
        (POSITION_Y, greeting.position.strip(), SIGN_PT),
        (NAME_Y, _spaced(greeting.name.strip()), NAME_PT),
    )
    for y, text, size in signature:
        if text:
            page.texts.append(TextItem(SIGN_RIGHT, y, text, size, Align.RIGHT))
    return page
