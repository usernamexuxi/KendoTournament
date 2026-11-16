"""대회 종별 표: 요강이 정한 개인전·단체전 종별 목록. 부문 규칙의 기본이 된다.

대회마다 종별이 다르다(rm/ 자료). 광명 회장기는 남초를 두 학년씩, 광명 시장기는 남초 개인전을 학년마다 나누고,
전국대회는 나이 구간까지 다르다. 그래서 고정값이 아니라 대회 파일에 저장하는 표다.
글은 신청서에 적힌 그대로 둔다 — 같은 글이 선수·팀의 종별로도 저장되어 서로 맞춰 보기 쉽다.
"""

from __future__ import annotations

from dataclasses import dataclass

from kendo_tournament.domain.division.category_label import parse_category


@dataclass(frozen=True)
class CategoryTable:
    individual: tuple[str, ...]
    team: tuple[str, ...]

    def unreadable(self) -> list[str]:
        """성별·학년을 알아볼 수 없는 종별 글. 이런 줄로는 부문을 만들 수 없다."""
        return [label for label in (*self.individual, *self.team) if parse_category(label) is None]


# 제19회 광명시회장기검도대회요강.hwp 의 신청서 양식 그대로(개인전 12개부, 단체전 6개부, 단체전 남녀 혼성).
GWANGMYEONG_CHAIRMAN = CategoryTable(
    individual=(
        "남초등 1~2학년",
        "남초등 3~4학년",
        "남초등 5~6학년",
        "여초등 1~3학년",
        "여초등 4~6학년",
        "여청소년 (중,고)",
        "중등부",
        "고등부",
        "남자청년부 20~35세",
        "남자장년부 36~47세",
        "남자중년부 48세부터",
        "여자일반부",
    ),
    team=(
        "초등저학년1~3학년",
        "초등고학년 4~6학년",
        "남청소년부(중,고)",
        "여청소년부(중,고)",
        "여자일반부",
        "남자일반부",
    ),
)

# 제26회 광명시장기 카탈로그·2026 경기일정의 부문 그대로. 성인 나이는 카탈로그에 없어 회장기 요강의 나이를 따랐다.
GWANGMYEONG_MAYOR = CategoryTable(
    individual=(
        "남초등 1학년",
        "남초등 2학년",
        "남초등 3학년",
        "남초등 4학년",
        "남초등 5학년",
        "남초등 6학년",
        "여초등 1~3학년",
        "여초등 4~6학년",
        "여청소년 (중,고)",
        "남중등부",
        "남고등부",
        "남자청년부 20~35세",
        "남자장년부 36~47세",
        "남자중년부 48세부터",
        "여자일반부",
    ),
    team=(
        "남초등 1~2학년",
        "남초등 3~4학년",
        "남초등 5~6학년",
        "여초등 1~3학년",
        "여초등 4~6학년",
        "남청소년부(중,고)",
        "여청소년부(중,고)",
        "여자일반부",
        "남자일반부",
    ),
)

# 2026 제28회 하늘내린 인제군수기 전국 검도대회 요강 · 신청서 그대로. 초등부는 남녀 구분 없이 학년으로만 나눈다.
INJE_NATIONAL = CategoryTable(
    individual=(
        "1,2학년",
        "3,4학년",
        "5,6학년",
        "여중부",
        "남중부",
        "고등부",
        "여자부",
        "20대 청년부",
        "30대 장년부",
        "40대 중년부",
        "50대이상 노년부",
    ),
    team=(
        "초등1~2학년부",
        "초등3~4학년부",
        "초등5~6학년부",
        "여중부",
        "남중부",
        "고등부",
        "여자부",
        "청년부",
        "장년부",
        "중년부",
        "노년부",
    ),
)

TEMPLATES: dict[str, CategoryTable] = {
    "광명 회장기": GWANGMYEONG_CHAIRMAN,
    "광명 시장기": GWANGMYEONG_MAYOR,
    "인제 전국대회": INJE_NATIONAL,
}
DEFAULT_CATEGORY_TABLE = GWANGMYEONG_CHAIRMAN
