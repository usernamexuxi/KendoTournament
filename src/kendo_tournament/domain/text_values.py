"""신청서·화면에 적힌 글자를 도메인 값으로 읽는다(성별·나이). 학년은 division/grade.py 가 맡는다."""

from __future__ import annotations

import re

from kendo_tournament.domain.model import Gender

GENDER_WORDS = {
    Gender.MALE: ("남", "남자", "남성", "m", "male"),
    Gender.FEMALE: ("여", "여자", "여성", "f", "female"),
}
MAX_AGE_DIGITS = 3


def parse_gender(text: str) -> Gender | None:
    key = re.sub(r"\s+", "", text or "").lower()
    for gender, words in GENDER_WORDS.items():
        if key in words:
            return gender
    return None


def parse_age(text: str) -> int | None:
    digits = re.sub(r"[^0-9]", "", text or "")
    return int(digits) if digits and len(digits) <= MAX_AGE_DIGITS else None
