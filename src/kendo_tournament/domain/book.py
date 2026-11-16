"""책자로 찍을 때의 설정: 가져온 표지 파일, 표지와 대진표 사이에 넣을 문서, 앞쪽 내용, 사진 표지."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from kendo_tournament.domain.greeting import DEFAULT_GREETING, Greeting
from kendo_tournament.domain.photo_cover import PhotoCoverSettings
from kendo_tournament.domain.program import DEFAULT_PROGRAM, ProgramContent


class GreetingSource(Enum):
    """전국 대회에서 「대회사」 쪽을 무엇으로 채울지. 광명 대회는 늘 프로그램 틀(TEMPLATE)이다."""

    TEMPLATE = "틀"
    NONE = "빼기"
    FILE = "파일"


@dataclass(frozen=True)
class BookSettings:
    """inserts 는 넣을 파일 경로(순서대로).

    cover_file 은 누가 따로 만들어 온 앞표지 파일 경로다. 있으면 사진 표지 대신 그 파일을 그대로 앞표지로 쓴다.
    back_cover_file 은 따로 만들어 온 뒤표지 파일 경로다. 있으면 그대로 뒤표지로 쓴다.
    program 은 표지·대회사 다음에 싣는 대회식순·대회임원·일정안내 내용이다.
    photo_cover 는 사진 표지(배경 사진 + 정해진 자리의 글)다. 사진을 안 골랐으면 카탈로그 사진을 쓴다.
    greeting 은 앞표지 다음 「대회사」 쪽 내용(사진·본문·날짜·직함·이름)이다.
    team_members 면 단체전 대진표의 팀 상자 밑에 팀원 이름을 싣는다(운영자가 출력 화면에서 켜고 끈다).
    greeting_source 는 전국 대회의 대회사 쪽 선택(None 이면 아직 안 골라 「빼기」), greeting_file 은 FILE 일 때 넣을 파일이다.
    """

    inserts: tuple[str, ...] = ()
    cover_file: str = ""
    back_cover_file: str = ""
    program: ProgramContent = DEFAULT_PROGRAM
    team_members: bool = True
    greeting: Greeting = DEFAULT_GREETING
    photo_cover: PhotoCoverSettings = PhotoCoverSettings()
    greeting_source: GreetingSource | None = None
    greeting_file: str = ""
