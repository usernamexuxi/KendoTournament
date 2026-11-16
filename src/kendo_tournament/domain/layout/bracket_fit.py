"""양쪽 대진표의 가로 맞춤: 회전 사이 간격을 먼저 확보하고 남는 폭을 이름 칸에 준다.

회전 사이가 좁으면 경기 번호가 옆 이름 위에 겹친다(운영자 지적 — 50명 대진을 한 쪽에 넣었을 때).
그래서 회전마다 MIN_ROUND_STEP 을 먼저 떼고, 남는 폭에 이름표가 안 들면 글자를 줄이지 않고
대진을 나눈다(글자 크기는 고정이다, bracket_parts).
"""

from __future__ import annotations

import unicodedata

from kendo_tournament.domain.layout.primitives import MM_PER_PT

MIN_ROUND_STEP = 9.0

# 들어가는지 판단할 때는 PDF 글꼴(Pretendard)의 실제 글자 폭(em)으로 잰다. 배치용 어림(primitives.estimated_width_mm)은
# 한글을 1em 으로 넉넉히 잡아 바깥 여백이 생기는데, 그 어림으로 판단하면 실제로는 들어가는 10명 대진도 나뉘었다.
PRINT_WIDE_EM = 0.87
PRINT_NARROW_EM = {"(": 0.35, ")": 0.35, " ": 0.26, ",": 0.26, ".": 0.26, **dict.fromkeys("0123456789", 0.44)}
PRINT_OTHER_EM = 0.6


def printed_width_mm(text: str, size_pt: float) -> float:
    """PDF 에 찍힐 때의 글자 폭(mm). 한글·한자는 0.87em, 괄호·공백·쉼표·마침표·숫자는 실제 폭, 나머지는 0.6em 으로 잡는다."""
    em = 0.0
    for char in text:
        if unicodedata.east_asian_width(char) in ("W", "F"):
            em += PRINT_WIDE_EM
        else:
            em += PRINT_NARROW_EM.get(char, PRINT_OTHER_EM)
    return em * size_pt * MM_PER_PT


def label_room(side_width: float, side_rounds: int) -> float:
    """한쪽 절반의 폭에서 회전 간격을 먼저 떼고 이름 칸에 남는 폭(mm)."""
    return side_width - side_rounds * MIN_ROUND_STEP
