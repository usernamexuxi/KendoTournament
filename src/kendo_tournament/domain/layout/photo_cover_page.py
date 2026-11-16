"""사진 앞표지·뒤표지 쪽. 글자 자리·크기·글꼴은 고정이고 내용만 바뀐다(운영자: 「폰트 위치 같게, 내용물만 수정」).

사진은 읽을 때 A4 비율로 가운데를 잘라 오므로(PhotoReader) 쪽 전체에 그대로 깐다.
"""

from __future__ import annotations

from dataclasses import dataclass

from kendo_tournament.domain.greeting import Photo
from kendo_tournament.domain.layout.bracket_fit import printed_width_mm
from kendo_tournament.domain.layout.bracket_style import WHITE
from kendo_tournament.domain.layout.primitives import (
    MM_PER_PT,
    PAGE_HEIGHT,
    PAGE_WIDTH,
    Align,
    Face,
    ImageItem,
    PageLayout,
    TextItem,
    middle_for_baseline,
)
from kendo_tournament.domain.photo_cover import BackCoverPhoto, CoverLogo

# 자리·크기는 카탈로그 PDF 의 글자 바닥선·크기를 A4 로 줄여(×0.980, 좌우 0.86mm 잘림) 옮겼다.
TITLE_LEFT = 15.7
TITLE_BASELINES = (37.4, 62.3, 87.2)
TITLE_STEP = TITLE_BASELINES[1] - TITLE_BASELINES[0]
ROUND_PT, TITLE_PT = 47.0, 58.8
TITLE_MAX_WIDTH = PAGE_WIDTH - TITLE_LEFT - 10.0
RIGHT_EDGE = 195.0
DATE_BASELINE, VENUE_BASELINE, DETAIL_PT = 261.5, 271.5, 23.3
CREDIT_BASELINE, CREDIT_LABEL_PT, CREDIT_PT = 283.9, 10.5, 13.4
# 카탈로그는 이름표와 내용 사이에 빈칸 하나, 묶음 사이에 빈칸 여섯(11.4pt 빈칸 폭 0.25em)을 둔다.
SPACE_MM = 11.4 * 0.25 * MM_PER_PT
LABEL_GAP, CREDIT_GAP = SPACE_MM, 6 * SPACE_MM
# 로고는 카탈로그 뒤표지에 박힌 로고와 같은 자리·크기(같은 방식으로 재서 옮김).
LOGO_LEFT, LOGO_BOTTOM = 12.9, 282.7
LOGO_HEIGHT, LOGO_MAX_WIDTH = 17.4, 60.0
# 오른쪽 아래 「한국관광의 별 · 한국대표관광지 100선 광명동굴」 묶음도 카탈로그 뒤표지와 같은 자리·폭.
BADGES_LEFT, BADGES_BOTTOM, BADGES_WIDTH = 129.5, 285.3, 70.8


@dataclass(frozen=True)
class PhotoCoverContent:
    """찍을 글. credits 는 (「주최」, 「광명시 체육회」) 같은 짝, 내용이 빈 짝은 빼고 넘긴다."""

    title_lines: tuple[str, ...]
    date_text: str
    venue: str
    credits: tuple[tuple[str, str], ...]


def _full_page(page: PageLayout, photo: Photo) -> None:
    page.images.append(ImageItem(0.0, 0.0, PAGE_WIDTH, PAGE_HEIGHT, photo.png))


def _line(page: PageLayout, text: str, size: float, baseline: float, align: Align, x: float, face: Face) -> None:
    y = middle_for_baseline(baseline, size)
    max_width = TITLE_MAX_WIDTH if face is Face.TITLE else None
    page.texts.append(TextItem(x, y, text, size, align, max_width=max_width, color=WHITE, face=face))


def _title(page: PageLayout, lines: tuple[str, ...]) -> None:
    """회차 줄(「제26회」)은 카탈로그처럼 조금 작게. 넷째 줄부터는 같은 간격으로 이어 내린다."""
    for index, line in enumerate(lines):
        size = ROUND_PT if index == 0 and len(lines) > 1 else TITLE_PT
        baseline = TITLE_BASELINES[0] + index * TITLE_STEP
        _line(page, line, size, baseline, Align.LEFT, TITLE_LEFT, Face.TITLE)


def _credits(page: PageLayout, credits: tuple[tuple[str, str], ...]) -> None:
    """맨 아래 「주최 ○○  주관 ○○  후원 ○○」를 오른쪽 끝에 맞춰 오른쪽부터 놓는다. 이름표는 작게."""
    right = RIGHT_EDGE
    for label, value in reversed(credits):
        _line(page, value, CREDIT_PT, CREDIT_BASELINE, Align.RIGHT, right, Face.BODY)
        right -= printed_width_mm(value, CREDIT_PT) + LABEL_GAP
        _line(page, label, CREDIT_LABEL_PT, CREDIT_BASELINE, Align.RIGHT, right, Face.BODY)
        right -= printed_width_mm(label, CREDIT_LABEL_PT) + CREDIT_GAP


def photo_front_cover(content: PhotoCoverContent, photo: Photo) -> PageLayout:
    page = PageLayout()
    _full_page(page, photo)
    _title(page, content.title_lines)
    for baseline, text in ((DATE_BASELINE, content.date_text), (VENUE_BASELINE, content.venue)):
        if text:
            _line(page, text, DETAIL_PT, baseline, Align.RIGHT, RIGHT_EDGE, Face.BODY)
    _credits(page, content.credits)
    return page


def photo_back_cover(back: BackCoverPhoto, city_logo: CoverLogo | None, badges: CoverLogo | None) -> PageLayout:
    """고른 사진에 카탈로그 뒤표지 아래쪽 로고들을 같은 자리에 얹는다(운영자: 「그 아래 가득한 로고들만 붙이고」).

    왼쪽 아래 광명시 로고는 자리가 어두우면 밝게 바꾼 판(on_dark), 밝으면 진한 판을 얹는다.
    오른쪽 아래 관광 로고 묶음은 색이 든 그림이라 그대로 얹는다(밝은 사진은 읽을 때 아래쪽을 눌러 둔다).
    """
    page = PageLayout()
    _full_page(page, back.photo)
    if city_logo is not None:
        height = min(LOGO_HEIGHT, LOGO_MAX_WIDTH / city_logo.aspect)
        width = height * city_logo.aspect
        image = city_logo.on_dark if back.logo_corner_dark and city_logo.on_dark else city_logo.png
        page.images.append(ImageItem(LOGO_LEFT, LOGO_BOTTOM - height, width, height, image))
    if badges is not None:
        height = BADGES_WIDTH / badges.aspect
        page.images.append(ImageItem(BADGES_LEFT, BADGES_BOTTOM - height, BADGES_WIDTH, height, badges.png))
    return page
