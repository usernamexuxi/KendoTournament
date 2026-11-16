"""대회 도메인 모델. 표준 라이브러리만 쓴다."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Gender(Enum):
    MALE = "남"
    FEMALE = "여"


class Event(Enum):
    INDIVIDUAL = "개인전"
    TEAM = "단체전"


ELEMENTARY_LAST = 6
MIDDLE_LAST = 9
HIGH_LAST = 12
ADULT = 13


@dataclass(frozen=True, order=True)
class Grade:
    """구분. 1~6 초1~6, 7~9 중1~3, 10~12 고1~3, 13 성인."""

    value: int

    def __post_init__(self) -> None:
        if not 1 <= self.value <= ADULT:
            raise ValueError(f"구분 값은 1~{ADULT} 이어야 합니다: {self.value}")

    @property
    def label(self) -> str:
        if self.value <= ELEMENTARY_LAST:
            return f"초{self.value}"
        if self.value <= MIDDLE_LAST:
            return f"중{self.value - ELEMENTARY_LAST}"
        if self.value <= HIGH_LAST:
            return f"고{self.value - MIDDLE_LAST}"
        return "성인"


ALL_GRADES = tuple(Grade(v) for v in range(1, ADULT + 1))


@dataclass(frozen=True)
class Participant:
    """category 는 개인전 신청서의 종별 글(예: 「남초등 1~2학년」). 그 양식은 학년을 안 적어 grade 는 범위의 첫 학년일 뿐이다."""

    id: str
    name: str
    gender: Gender | None
    dojang: str
    grade: Grade | None = None
    age: int | None = None
    region: str = ""
    source: str = ""
    category: str = ""


@dataclass(frozen=True)
class Team:
    """category 는 신청서에 적힌 팀 종별 글(예: 「초등저학년 1~3학년」). 종별 없는 양식·예전 파일은 빈 글이다.

    positions 는 member_ids 와 같은 순서의 자리(선봉·중견·주장·후보 …). 자리를 안 적는 양식·예전 파일은 빈 tuple 이다.
    """

    id: str
    name: str
    dojang: str
    member_ids: tuple[str, ...]
    category: str = ""
    positions: tuple[str, ...] = ()


@dataclass(frozen=True)
class Entry:
    """대진 칸 하나에 들어가는 출전 단위(선수 또는 팀). team 이면 단체전 팀이라 칸에 「도장+팀 이름」만 쓴다."""

    id: str
    name: str
    dojang: str
    team: bool = False


@dataclass(frozen=True)
class DivisionRule:
    id: str
    event: Event
    gender: Gender | None
    grade_from: Grade
    grade_to: Grade
    # 팀 인원은 신청서에 적힌 팀원 그대로라 규칙이 정하지 않는다(운영자). 예전 파일에 남은 값을 읽으려고만 둔다.
    team_size: int | None = None
    min_entries: int | None = None
    age_from: int | None = None
    age_to: int | None = None
    age_name: str = ""

    def __post_init__(self) -> None:
        if self.grade_from > self.grade_to:
            raise ValueError("구분 범위의 시작이 끝보다 큽니다.")

    @property
    def label(self) -> str:
        gender = self.gender.value + "자" if self.gender else "혼성"
        if self.grade_from == self.grade_to:
            grades = self.grade_from.label
        else:
            grades = f"{self.grade_from.label}~{self.grade_to.label}"
        if self.has_age_band:
            grades = self.age_band_label
        elif self.age_name:
            grades = self.age_name
        return f"{gender} {grades} {self.event.value}"

    @property
    def has_age_band(self) -> bool:
        """성인 부문을 나이로 나눈 규칙인가(청년부 20~35세 처럼). age_to 가 없으면 「~세부터」."""
        return self.age_from is not None

    @property
    def age_band_label(self) -> str:
        span = f"{self.age_from}세부터" if self.age_to is None else f"{self.age_from}~{self.age_to}세"
        return f"{self.age_name}({span})" if self.age_name else span

    def age_fits(self, age: int | None) -> bool:
        if not self.has_age_band:
            return True
        if age is None or self.age_from is None or age < self.age_from:
            return False
        return self.age_to is None or age <= self.age_to


@dataclass(frozen=True)
class Division:
    rule_ids: tuple[str, ...]
    label: str
    event: Event
    entries: tuple[Entry, ...] = field(default_factory=tuple)
