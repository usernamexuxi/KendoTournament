"""신청서의 「종별」 글(남초등 1~2학년 · 여청소년(중,고) · 남자청년부 20~35세 …)을 성별·학년·나이 범위로 읽는다.

실제 광명시 회장기 신청서는 선수마다 성별·학년을 적지 않고, 「종별」 줄에 이름만 늘어놓는다.
그래서 선수의 성별·학년(성인은 나이)은 그 종별에서 가져온다 — 학년은 범위의 첫 학년, 나이는 범위의 첫 나이.
대진은 같은 범위로 만든 부문 규칙에 들어가므로 첫 값만으로 맞는 부문을 찾는다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from kendo_tournament.domain.model import ADULT, ELEMENTARY_LAST, HIGH_LAST, MIDDLE_LAST, Gender

# 「1,2학년」처럼 쉼표로 잇는 양식도 있다(인제 전국대회).
_RANGE = re.compile(r"(\d+)\s*[~\-,]\s*(\d+)")
_SINGLE = re.compile(r"(\d+)")
_AGE_FROM = re.compile(r"(\d+)\s*세\s*(부터|이상)")
DECADE_SPAN = 9
_OPEN_END = re.compile(r"세\s*(이상|부터)")
_AGE_RANGE = re.compile(r"(\d+)\s*세?\s*[~\-]\s*(\d+)\s*세")
ADULT_WORDS = ("일반", "청년", "장년", "중년", "노년", "성인")
_DECADE = re.compile(r"(\d+)\s*대\s*(이상)?")
_SHORT_SCHOOL = re.compile(r"^(남|여)?(중|고)부")
# 인제 전국대회 요강: 「여자부 : 고등학생 이상」. 성별만 적은 「여자부」·「남자부」는 고등부부터 성인까지다.
_GENDER_ONLY = ("여자부", "남자부")
# 학년 숫자 없이 「초등/저학년부」라고만 적은 양식이 있다. 범위는 요강의 「초등저학년1~3학년 · 초등고학년 4~6학년」.
ELEMENTARY_HALVES = (("저학년", (1, 3)), ("고학년", (4, ELEMENTARY_LAST)))
YOUTH_WORDS = ("청소년",)


@dataclass(frozen=True)
class Category:
    gender: Gender | None
    grade_from: int
    grade_to: int
    age_from: int | None = None
    age_to: int | None = None


def _gender(text: str) -> Gender | None:
    if text.startswith("남") or "남자" in text:
        return Gender.MALE
    if text.startswith("여") or "여자" in text:
        return Gender.FEMALE
    return None


def _school_span(text: str) -> tuple[int, int] | None:
    if text in _GENDER_ONLY:
        return MIDDLE_LAST + 1, ADULT
    short = _SHORT_SCHOOL.match(text)
    if short:
        return (ELEMENTARY_LAST + 1, MIDDLE_LAST) if short.group(2) == "중" else (MIDDLE_LAST + 1, HIGH_LAST)
    if any(word in text for word in ADULT_WORDS):
        return ADULT, ADULT
    if any(word in text for word in YOUTH_WORDS) or ("중" in text and "고" in text and "(" in text):
        return ELEMENTARY_LAST + 1, HIGH_LAST
    if "초" in text or ("학년" in text and "중" not in text and "고" not in text):
        span = _RANGE.search(text)
        if span:
            return int(span.group(1)), int(span.group(2))
        single = _SINGLE.search(text)
        if single:
            return (int(single.group(1)),) * 2
        return next((span for word, span in ELEMENTARY_HALVES if word in text), (1, ELEMENTARY_LAST))
    if "중등" in text or text.startswith("중"):
        return ELEMENTARY_LAST + 1, MIDDLE_LAST
    if "고등" in text or text.startswith("고"):
        return MIDDLE_LAST + 1, HIGH_LAST
    return None


def _ages(text: str) -> tuple[int | None, int | None]:
    decade = _DECADE.search(text)
    if decade:
        start = int(decade.group(1))
        return start, None if decade.group(2) else start + DECADE_SPAN
    span = _AGE_RANGE.search(text)
    if span:
        # 「40~50세이상」 은 40세부터다(광명인화검도관 신청서). 「이상·부터」가 붙으면 끝을 열어 둔다.
        open_end = _OPEN_END.search(text) is not None
        return int(span.group(1)), None if open_end else int(span.group(2))
    start = _AGE_FROM.search(text)
    return (int(start.group(1)), None) if start else (None, None)


_AGE_PART = re.compile(r"\d+\s*(대|세)?\s*(이상|부터)?|[~\-]")
_GENDER_PREFIX = re.compile(r"^(남자|여자|남|여)")
BAND_WORDS = ("청년", "장년", "중년", "노년")


def band_name(label: str) -> str:
    """성인 종별의 부 이름. 「남자청년부 20~35세」 → 「청년부」, 「40대 중년부」 → 「중년부」. 나이·성별 글을 뗀다."""
    text = _AGE_PART.sub("", re.sub(r"\s+", "", label))
    return _GENDER_PREFIX.sub("", text)


def group_name(label: str) -> str:
    """요강이 초등부를 「저학년부·고학년부」로 부르면 그 이름(「초등 저학년부」). 아니면 빈 글.

    운영자: 요강의 초등부 이름이 학년 대신 저학년부·고학년부로 바뀔 수 있다 — 대진표 제목도 요강 이름을 따른다.
    글이 가리키는 학년 범위가 그 이름의 범위(1~3·4~6)와 다르면 이름을 붙이지 않는다(「저학년 1~2학년」 같은 글).
    """
    category = parse_category(label)
    if category is None:
        return ""
    for word, span in ELEMENTARY_HALVES:
        if word in label and (category.grade_from, category.grade_to) == span:
            return f"초등 {word}부"
    return ""


def has_band_word(label: str) -> bool:
    return any(word in label for word in BAND_WORDS)


def parse_category(label: str) -> Category | None:
    """종별 글을 읽는다. 학교급을 알아볼 수 없으면 None (예: 「26명 참가」 같은 메모)."""
    text = re.sub(r"\s+", "", label)
    span = _school_span(text)
    if span is None:
        return None
    age_from, age_to = _ages(label) if span[0] == ADULT else (None, None)
    return Category(_gender(text), span[0], span[1], age_from, age_to)


def fill_missing_gender(categories: list[Category]) -> list[Category]:
    """성별이 안 적힌 종별(「중등부」)은, 같은 학년대에 다른 성별 종별(「여청소년(중,고)」)이 있으면 그 반대 성별이다.

    실제 요강: 「남중등부, 남고등부, 여자청소년부(중,고)」인데 신청서 줄에는 「중등부」「고등부」만 적혀 있다.
    반대 성별을 짐작할 근거가 없으면 그대로 둔다(명단에서 운영자가 고친다).
    """
    filled = []
    for category in categories:
        if category.gender is not None:
            filled.append(category)
            continue
        others = {
            other.gender
            for other in categories
            if other.gender is not None and other.grade_from <= category.grade_to and category.grade_from <= other.grade_to
        }
        if len(others) == 1:
            known = others.pop()
            opposite = Gender.FEMALE if known is Gender.MALE else Gender.MALE
            filled.append(Category(opposite, category.grade_from, category.grade_to, category.age_from, category.age_to))
        else:
            filled.append(category)
    return filled
