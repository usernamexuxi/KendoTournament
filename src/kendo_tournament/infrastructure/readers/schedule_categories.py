"""경기일정 문서의 「경기장배치」 표에서 종별을 읽는다(운영자: 「요강 신청서 읽기에서 경기일정 파일을 못 읽는다」).

경기일정에는 신청서 양식이 없고, 머리 「제1경기장 | 제2경기장」 아래 칸마다
「남초등부 1학년부 개인전 남초등부 2학년부 개인전 남초등부1~2학년 단체전 …」처럼 부문이 이어 적혀 있다.
「개인전」·「단체전」 낱말을 경계로 잘라 그 앞 글을 종별로 삼는다. 신청서 양식의 종별이 있으면 그쪽이 먼저다.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

_COURT = re.compile(r"^제\s*\d+\s*경기장$")
INDIVIDUAL_WORD = "개인전"
TEAM_WORD = "단체전"
# 「여자청소년부개인전(중.고)」처럼 괄호가 낱말 뒤에 붙기도 하고, 「남자일반부 단체전A」처럼 묶음 글자가 붙기도 한다.
_ENTRY = re.compile(rf"(?P<label>.+?)\s*(?P<event>{INDIVIDUAL_WORD}|{TEAM_WORD})\s*(?P<note>\([^)]*\))?[A-Z]?(?=\s|$)")


def is_court_table(rows: Sequence[Sequence[str]]) -> bool:
    """머리 줄이 모두 「제n경기장」인 표."""
    if not rows or not rows[0]:
        return False
    return all(_COURT.match(re.sub(r"\s+", "", cell)) for cell in rows[0] if cell.strip())


def court_categories(rows: Sequence[Sequence[str]]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(개인전 종별, 단체전 종별)을 표에 나온 순서대로, 같은 글은 한 번만."""
    individual: list[str] = []
    team: list[str] = []
    for row in rows[1:]:
        for cell in row:
            for match in _ENTRY.finditer(" ".join(cell.split())):
                label = (match.group("label").strip() + (match.group("note") or "")).strip()
                target = individual if match.group("event") == INDIVIDUAL_WORD else team
                if label and label not in target:
                    target.append(label)
    return tuple(individual), tuple(team)
