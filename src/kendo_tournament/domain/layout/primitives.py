"""종이 위에 그릴 기본 요소(글자·선·면·그림)와 A4 치수. 단위는 mm, 원점은 왼쪽 위다. 색은 「#rrggbb」."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from enum import Enum

PAGE_WIDTH = 210.0
PAGE_HEIGHT = 297.0
MM_PER_PT = 0.3528
WIDE_CHAR_EM = 1.0
NARROW_CHAR_EM = 0.56
INK = "#262626"
# 출력기는 y 를 글자 높이의 가운데로 보고, 글자 바닥선을 그보다 크기×0.35 아래에 찍는다.
BASELINE_SHIFT = 0.35


class Align(Enum):
    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"


class Face(Enum):
    """글꼴. BODY 는 Pretendard(보통·굵게), TITLE 은 표지 제목 글꼴(충주김생체 — 참고 카탈로그와 같은 글꼴)."""

    BODY = "body"
    TITLE = "title"


@dataclass(frozen=True)
class TextItem:
    x: float
    y: float
    text: str
    size_pt: float
    align: Align
    bold: bool = False
    max_width: float | None = None
    slot: int | None = None
    color: str = INK
    face: Face = Face.BODY


def middle_for_baseline(baseline_mm: float, size_pt: float) -> float:
    """바닥선 자리(mm)를 TextItem.y(글자 가운데)로 바꾼다. 남의 PDF 를 재서 맞출 때는 바닥선이 재기 쉽다."""
    return baseline_mm - size_pt * BASELINE_SHIFT * MM_PER_PT


@dataclass(frozen=True)
class LineItem:
    x1: float
    y1: float
    x2: float
    y2: float
    width_pt: float = 0.8


@dataclass(frozen=True)
class RectItem:
    x: float
    y: float
    width: float
    height: float
    fill: str


@dataclass(frozen=True)
class PolygonItem:
    points: tuple[tuple[float, float], ...]
    fill: str


@dataclass(frozen=True)
class ImageItem:
    """PNG 그림 한 장. 끼워 넣은 PDF 쪽을 그림으로 실을 때 쓴다."""

    x: float
    y: float
    width: float
    height: float
    png: bytes


@dataclass
class PageLayout:
    """그리는 순서: 면(rects) → 다각형 → 그림 → 선 → 글자. 뒤에 그린 것이 위에 온다."""

    texts: list[TextItem] = field(default_factory=list)
    lines: list[LineItem] = field(default_factory=list)
    rects: list[RectItem] = field(default_factory=list)
    polygons: list[PolygonItem] = field(default_factory=list)
    images: list[ImageItem] = field(default_factory=list)
    width: float = PAGE_WIDTH
    height: float = PAGE_HEIGHT


def estimated_width_mm(text: str, size_pt: float) -> float:
    """글꼴을 모르는 domain 에서 쓰는 어림 너비. 한글·한자는 1em, 나머지는 약 0.56em 으로 잡는다.

    실제 너비와 조금 달라도 출력기가 max_width 를 넘는 글자를 줄여 맞추므로 넘치지는 않는다.
    """
    em = sum(WIDE_CHAR_EM if unicodedata.east_asian_width(ch) in ("W", "F") else NARROW_CHAR_EM for ch in text)
    return em * size_pt * MM_PER_PT
