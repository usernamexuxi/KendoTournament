"""문서 형식과 상관없이 「표 = 글자 칸의 행 목록」을 명단으로 바꾼다.

머리글은 아래 동의어 목록(허용 목록)과 맞춰 찾는다. 샘플 신청서를 받으면 이 목록만 고치면 된다.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum

from kendo_tournament.domain.division.grade import parse_school_grade
from kendo_tournament.domain.model import Participant, Team
from kendo_tournament.domain.text_values import parse_age, parse_gender


class Column(Enum):
    NAME = "이름"
    GENDER = "성별"
    GRADE = "학년"
    SCHOOL = "학교"
    AGE = "나이"
    DOJANG = "도장"
    REGION = "지역"
    TEAM = "팀"


HEADER_SYNONYMS: dict[Column, tuple[str, ...]] = {
    Column.NAME: ("이름", "성명", "선수명", "선수이름", "성함"),
    Column.GENDER: ("성별", "남녀", "구분(남/여)"),
    Column.GRADE: ("학년", "학년(학교)", "학교/학년"),
    Column.SCHOOL: ("학교", "학교명", "소속학교", "재학학교"),
    Column.AGE: ("나이", "연령", "만나이", "연나이"),
    Column.DOJANG: ("도장", "도장명", "검도장", "소속", "소속도장", "관명", "도장이름", "단체명"),
    Column.REGION: ("지역", "시도", "시/도", "지역명"),
    Column.TEAM: ("팀", "팀명", "단체전", "단체전팀", "단체팀"),
}
HEADER_SEARCH_ROWS = 4
_KEY_VALUE = re.compile(r"^\s*(?P<key>[^:：]+?)\s*[:：]\s*(?P<value>.+?)\s*$")


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text or "").lower()


def column_of(header: str) -> Column | None:
    key = _compact(header)
    for column, words in HEADER_SYNONYMS.items():
        if key in (_compact(word) for word in words):
            return column
    return None


def dojang_from_text(text: str) -> str | None:
    """「도장명: ○○검도관」 같은 줄에서 도장명을 꺼낸다."""
    match = _KEY_VALUE.match(text or "")
    if match and column_of(match.group("key")) is Column.DOJANG:
        return match.group("value")
    return None


@dataclass
class TableParse:
    participants: list[Participant] = field(default_factory=list)
    teams: list[Team] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    recognized: bool = False


def _find_header(rows: Sequence[Sequence[str]]) -> tuple[int, dict[Column, int]] | None:
    for index, row in enumerate(rows[:HEADER_SEARCH_ROWS]):
        columns = {}
        for position, cell in enumerate(row):
            column = column_of(cell)
            if column is not None and column not in columns:
                columns[column] = position
        if Column.NAME in columns:
            return index, columns
    return None


def dojang_in_rows(rows: Sequence[Sequence[str]]) -> str | None:
    """표 안에 「도장명 | ○○검도관」 이나 「도장명: ○○검도관」 이 있으면 꺼낸다."""
    for row in rows:
        for position, cell in enumerate(row):
            inline = dojang_from_text(cell)
            if inline:
                return inline
            if column_of(cell) is Column.DOJANG and position + 1 < len(row) and row[position + 1].strip():
                return row[position + 1].strip()
    return None


def _cell(row: Sequence[str], columns: dict[Column, int], column: Column) -> str:
    position = columns.get(column)
    if position is None or position >= len(row):
        return ""
    return row[position].strip()


def _parse_row(row, columns, context_dojang, where, problems) -> tuple[Participant, str] | None:
    name = _cell(row, columns, Column.NAME)
    if not name:
        return None
    dojang = _cell(row, columns, Column.DOJANG) or context_dojang or ""
    gender = parse_gender(_cell(row, columns, Column.GENDER))
    grade_text = _cell(row, columns, Column.GRADE)
    school = _cell(row, columns, Column.SCHOOL)
    grade = parse_school_grade(school, grade_text) if grade_text else None
    age = parse_age(_cell(row, columns, Column.AGE))
    if not dojang:
        problems.append(f"{where} {name}: 도장명을 찾지 못했습니다.")
    if gender is None:
        problems.append(f"{where} {name}: 성별을 읽지 못했습니다.")
    if grade_text and grade is None:
        shown = f"{school} {grade_text}".strip()
        problems.append(f"{where} {name}: 학년 「{shown}」을(를) 알아볼 수 없습니다.")
    if grade is None and age is None:
        problems.append(f"{where} {name}: 학년이나 나이가 없습니다.")
    participant = Participant(
        id=where,
        name=name,
        gender=gender,
        dojang=dojang,
        grade=grade,
        age=age,
        region=_cell(row, columns, Column.REGION),
        source=where.split("#")[0],
    )
    return participant, _cell(row, columns, Column.TEAM)


def parse_table(rows: Sequence[Sequence[str]], context_dojang: str | None, source: str, table_no: int) -> TableParse:
    result = TableParse()
    found = _find_header(rows)
    if found is None:
        return result
    header_index, columns = found
    result.recognized = True
    dojang = dojang_in_rows(rows[:header_index]) or context_dojang
    team_members: dict[tuple[str, str], list[str]] = {}
    for row_no, row in enumerate(rows[header_index + 1 :], start=1):
        where = f"{source}#{table_no}-{row_no}"
        parsed = _parse_row(row, columns, dojang, where, result.problems)
        if parsed is None:
            continue
        participant, team = parsed
        result.participants.append(participant)
        if team:
            team_members.setdefault((participant.dojang, team), []).append(participant.id)
    for (team_dojang, team_name), members in team_members.items():
        team_id = f"{source}#팀-{team_dojang}-{team_name}"
        result.teams.append(Team(team_id, f"{team_dojang} {team_name}", team_dojang, tuple(members)))
    return result
