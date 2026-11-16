"""참고 책자의 꾸밈: 부문 이름을 담는 남색 띠(아래 모서리가 둥근 탭)와 가운데 「결승전」 표시."""

from __future__ import annotations

import math

from kendo_tournament.domain.layout.primitives import PAGE_WIDTH, Align, PageLayout, PolygonItem, TextItem

NAVY = "#3b3d52"
TAB_WIDTH = 82.0
TAB_HEIGHT = 9.5
TAB_RADIUS = 4.5
TAB_PT = 14.0
FINAL_LABEL = "결승전"
FINAL_WIDTH = 15.0
FINAL_HEIGHT = 6.4
FINAL_RADIUS = 1.2
FINAL_PT = 9.5
ARC_STEPS = 8
WHITE = "#ffffff"


def _arc(cx: float, cy: float, radius: float, start_deg: float, end_deg: float) -> list[tuple[float, float]]:
    points = []
    for step in range(ARC_STEPS + 1):
        angle = math.radians(start_deg + (end_deg - start_deg) * step / ARC_STEPS)
        points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return points


def draw_title_tab(page: PageLayout, title: str, top: float) -> float:
    """쪽 가운데에 부문 이름 띠를 그리고 띠 아래끝 y 를 돌려준다. 위는 반듯, 아래 두 모서리는 둥글다."""
    left, right, bottom = (PAGE_WIDTH - TAB_WIDTH) / 2, (PAGE_WIDTH + TAB_WIDTH) / 2, top + TAB_HEIGHT
    points = [(left, top), (right, top)]
    points += _arc(right - TAB_RADIUS, bottom - TAB_RADIUS, TAB_RADIUS, 0, 90)
    points += _arc(left + TAB_RADIUS, bottom - TAB_RADIUS, TAB_RADIUS, 90, 180)
    page.polygons.append(PolygonItem(tuple(points), NAVY))
    page.texts.append(TextItem(PAGE_WIDTH / 2, top + TAB_HEIGHT / 2, title, TAB_PT, Align.CENTER, bold=True, color=WHITE))
    return bottom


def draw_final_label(page: PageLayout, center: float, y: float) -> None:
    """결승선 가운데의 둥근 남색 상자와 흰 「결승전」 글자."""
    left, right = center - FINAL_WIDTH / 2, center + FINAL_WIDTH / 2
    top, bottom = y - FINAL_HEIGHT / 2, y + FINAL_HEIGHT / 2
    points = _arc(right - FINAL_RADIUS, top + FINAL_RADIUS, FINAL_RADIUS, 270, 360)
    points += _arc(right - FINAL_RADIUS, bottom - FINAL_RADIUS, FINAL_RADIUS, 0, 90)
    points += _arc(left + FINAL_RADIUS, bottom - FINAL_RADIUS, FINAL_RADIUS, 90, 180)
    points += _arc(left + FINAL_RADIUS, top + FINAL_RADIUS, FINAL_RADIUS, 180, 270)
    page.polygons.append(PolygonItem(tuple(points), NAVY))
    page.texts.append(TextItem(center, y, FINAL_LABEL, FINAL_PT, Align.CENTER, bold=True, color=WHITE))
