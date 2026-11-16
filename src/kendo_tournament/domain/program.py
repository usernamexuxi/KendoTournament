"""책자 앞쪽 내용: 대회식순 · 대회임원 · 일정안내. 틀은 참고 책자(광명시장기 카탈로그)이고 내용은 운영자가 고친다.

운영자는 화면의 표에 한 줄에 한 항목씩 왼쪽·오른쪽 칸을 적는다(예: 개회식통보 · 사회자).
기본값은 참고 책자의 항목 이름만 가져오고 사람 이름은 비워 둔다.
"""

from __future__ import annotations

from dataclasses import dataclass

Row = tuple[str, str]


@dataclass(frozen=True)
class ProgramContent:
    opening: tuple[Row, ...]
    closing: tuple[Row, ...]
    officials: tuple[Row, ...]
    schedule: tuple[Row, ...]
    match_guide: tuple[Row, ...]
    guide_notes: tuple[str, ...]
    courts: tuple[Row, ...]
    court_rules: tuple[str, ...]


DEFAULT_PROGRAM = ProgramContent(
    opening=(
        ("개회식통보", "사회자"),
        ("내빈소개", "사회자"),
        ("국민의례", "사회자"),
        ("개회선언", "임원장"),
        ("대회사", ""),
        ("축사", ""),
        ("심판장주의사항", "심판장"),
        ("선수대표선서", "선수대표"),
        ("선수단경기", "전체"),
    ),
    closing=(
        ("폐회식통보", "사회자"),
        ("성적발표", "사회자"),
        ("시상", "사회자"),
        ("폐회선언", "임원장"),
    ),
    officials=(
        ("대회고문", ""),
        ("대회장", ""),
        ("부대회장", ""),
        ("임원장", ""),
        ("심판장", ""),
        ("심판", ""),
        ("경기부장", ""),
        ("진행요원", ""),
    ),
    schedule=(("심판회의", ""), ("개회식", ""), ("경기시작", "")),
    match_guide=(("경기시간", ""),),
    guide_notes=(
        "무승부일 경우, 연장전(단판승부) 실시",
        "경기 상황에 따라 경기장과 시간이 변경될 수 있으니, 원활한 경기 진행을 위하여 본부석의 안내에 따라주시기를 부탁드립니다.",
    ),
    courts=(("제1경기장", ""), ("제2경기장", "")),
    court_rules=(
        "명랑하고 질서 있는 응원을 합시다.",
        "경기장 내에서는 ID카드를 소지한 임원 및 선수만 출입합시다.",
        "경기장 전 구역에서 담배를 피우지 맙시다.",
        "경기장에서 오물을 버리지 맙시다.",
        "승자에게 축하, 패자에게는 격려를 아끼지 맙시다.",
    ),
)
