"""신청서의 학년·나이 표기를 구분(Grade)으로 바꾼다."""

from __future__ import annotations

import re

from kendo_tournament.domain.model import ADULT, ELEMENTARY_LAST, HIGH_LAST, MIDDLE_LAST, Grade, Participant

_FIRST_AGE = 8
_LEVEL_OFFSET = {"초": 0, "중": ELEMENTARY_LAST, "고": MIDDLE_LAST}
_LEVEL_MAX = {"초": 6, "중": 3, "고": 3}
_GRADE_PATTERN = re.compile(r"^(초|중|고)(?:등|등학교|학교)?(\d)(?:학년)?$")
_ADULT_WORDS = ("성인", "일반", "대학")
_SCHOOL_LEVEL = re.compile(r"(초|중|고)(?:등학교|학교|교)?$")
_GRADE_NUMBER = re.compile(r"^(\d)(?:학년)?$")


def parse_grade(text: str) -> Grade | None:
    """「초3」「초등 3」「중1」「고 2」「성인」을 읽는다. 학교급이 없으면 None."""
    compact = re.sub(r"\s+", "", text or "")
    if not compact:
        return None
    if any(word in compact for word in _ADULT_WORDS):
        return Grade(ADULT)
    match = _GRADE_PATTERN.match(compact)
    if not match:
        return None
    level, number = match.group(1), int(match.group(2))
    if not 1 <= number <= _LEVEL_MAX[level]:
        return None
    return Grade(_LEVEL_OFFSET[level] + number)


def parse_school_grade(school: str, grade_text: str) -> Grade | None:
    """학교 칸(「철산초등학교」)과 학년 칸(「3」)이 따로 적힌 신청서를 읽는다.

    학년 칸에 「초3」「일반」처럼 학교급까지 있으면 그것을 따른다.
    """
    own = parse_grade(grade_text)
    if own is not None:
        return own
    number = _GRADE_NUMBER.match(re.sub(r"\s+", "", grade_text or ""))
    level = _SCHOOL_LEVEL.search(re.sub(r"\s+", "", school or ""))
    if number is None or level is None:
        return None
    return parse_grade(f"{level.group(1)}{number.group(1)}")


def grade_from_age(age: int) -> Grade | None:
    """세는나이(한국 나이) 기준: 8세=초1 … 19세=고3, 20세 이상=성인. 8세 미만은 판단하지 않는다."""
    if age < _FIRST_AGE:
        return None
    value = age - _FIRST_AGE + 1
    if value > HIGH_LAST:
        return Grade(ADULT)
    return Grade(value)


def resolve_grade(participant: Participant) -> Grade | None:
    """적힌 학년을 그대로 우선하고, 없을 때만 나이로 계산한다."""
    if participant.grade is not None:
        return participant.grade
    if participant.age is not None:
        return grade_from_age(participant.age)
    return None
