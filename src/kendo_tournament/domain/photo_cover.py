"""사진 표지: 배경 사진 위에 정해진 자리·글꼴로 제목과 오른쪽 아래 글을 얹는다. 운영자는 내용만 고친다.

기준은 제26회 광명시장기 카탈로그(자체 제작)다. 앞표지는 왼쪽 위 세 줄 제목, 오른쪽 아래 날짜·장소,
맨 아래 주최·주관·후원이다. 뒤표지는 배경 사진과 왼쪽 아래 광명시 로고다.
사진을 고르지 않으면 카탈로그 앞표지 사진에 글을 얹고, 뒤표지는 카탈로그 뒤표지를 그대로 쓴다(광명 대회만, 전국 대회는 표지 없음).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from kendo_tournament.domain.greeting import Photo

DEFAULT_HOST = "광명시 체육회"
DEFAULT_ORGANIZER = "광명시 검도회"
DEFAULT_SPONSOR = "광명시, 광명시의회"
# 예전 판은 배포본 예시 사진을 「예시:파일이름」으로 저장했다. 예시는 뺐으므로 이 값은 「안 고름」(카탈로그)으로 읽는다.
EXAMPLE_PREFIX = "예시:"
_ROUND = re.compile(r"^(제\s*\d+\s*회)\s*(.*)$")
_TAIL = "검도대회"


@dataclass(frozen=True)
class PhotoCoverSettings:
    """photo·back_photo 는 사진 파일 경로다. 비면 카탈로그 앞·뒤표지를 쓴다. title_lines 가 비면 대회 이름을 세 줄로 나눠 쓴다(cover_title_lines).

    date_text 가 비면 대회 날짜.
    """

    photo: str = ""
    back_photo: str = ""
    title_lines: str = ""
    date_text: str = ""
    venue: str = ""
    host: str = DEFAULT_HOST
    organizer: str = DEFAULT_ORGANIZER
    sponsor: str = DEFAULT_SPONSOR


@dataclass(frozen=True)
class CoverChoice:
    """표지 사진으로 고를 수 있는 것 하나. ref 는 설정에 적을 값(빈 값 = 카탈로그), path 는 미리보기로 열 파일."""

    label: str
    ref: str
    path: Path


@dataclass(frozen=True)
class CoverLogo:
    """뒤표지 로고(PNG). aspect 는 가로÷세로. on_dark 는 어두운 바탕용으로 밝게 바꾼 판이다(None 이면 png 하나)."""

    png: bytes
    aspect: float
    on_dark: bytes | None = None


@dataclass(frozen=True)
class BackCoverPhoto:
    """운영자가 고른 뒤표지 사진. logo_corner_dark 면 왼쪽 아래(로고 자리)가 어두워 밝은 로고를 얹는다."""

    photo: Photo
    logo_corner_dark: bool


def cover_title_lines(title_lines: str, tournament_name: str) -> list[str]:
    """적어 둔 줄이 있으면 그대로, 없으면 「제26회 / 광명시장기 / 검도대회」처럼 대회 이름을 나눈다."""
    written = [line.strip() for line in title_lines.splitlines() if line.strip()]
    if written:
        return written
    name = tournament_name.strip()
    lines: list[str] = []
    match = _ROUND.match(name)
    if match:
        lines.append(match.group(1).replace(" ", ""))
        name = match.group(2).strip()
    if name.endswith(_TAIL) and name != _TAIL:
        lines += [name.removesuffix(_TAIL).strip(), _TAIL]
    elif name:
        lines.append(name)
    return lines
