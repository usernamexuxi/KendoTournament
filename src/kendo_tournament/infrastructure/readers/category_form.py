"""「종별 × 성명」 모양 신청서 표를 명단으로 바꾼다(실제 광명시 회장기 신청서 양식).

개인전 표: 머리 「종 별 | 성 명 | 성 명 …」, 줄마다 첫 칸이 종별(남초등 1~2학년 …)이고 나머지 칸에 이름이 늘어선다.
종별 칸이 빈 줄은 바로 위 종별의 이어지는 줄이다.
단체전 표: 머리 「A팀 | 성 명 | 생년 월일 | B팀 | …」, 줄마다 자리(선봉·중견·주장·후보)와 이름. 종별은 표 바로 앞
두 칸짜리 표(「○ | 초등고학년 4~6학년」)에 적힌다. 단체전은 남녀 혼성이라 팀원 성별은 비워 둔다(요강: 단체전 남, 여 혼성).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from kendo_tournament.domain.division.category_label import fill_missing_gender, parse_category
from kendo_tournament.domain.model import Team
from kendo_tournament.domain.written_form import participant_from_category as _person
from kendo_tournament.infrastructure.readers.table_rows import Column, TableParse, column_of

CATEGORY_HEADER = "종별"
NUMBER_HEADER = "번호"
MIN_COLUMN_CATEGORIES = 2
TEAM_SUFFIX = "팀"
TEAM_COLUMNS = 3


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def _is_row_grid(rows: Sequence[Sequence[str]]) -> bool:
    """「종 별 | 성 명 | 성 명 …」: 줄마다 종별, 옆으로 이름(광명 양식)."""
    head = rows[0]
    return _compact(head[0]) == CATEGORY_HEADER and any(column_of(cell) is Column.NAME for cell in head[1:])


def _is_column_grid(rows: Sequence[Sequence[str]]) -> bool:
    """「번호 | 1,2학년 | 3,4학년 | …」: 칸마다 종별, 아래로 이름(인제 전국대회 양식)."""
    head = rows[0]
    readable = [cell for cell in head[1:] if cell.strip() and parse_category(cell) is not None]
    return _compact(head[0]) == NUMBER_HEADER and len(readable) >= MIN_COLUMN_CATEGORIES


def is_category_grid(rows: Sequence[Sequence[str]]) -> bool:
    if not rows or len(rows[0]) < 2:
        return False
    return _is_row_grid(rows) or _is_column_grid(rows)


def is_team_grid(rows: Sequence[Sequence[str]]) -> bool:
    if not rows or len(rows[0]) < TEAM_COLUMNS:
        return False
    head = rows[0]
    return _compact(head[0]).endswith(TEAM_SUFFIX) and column_of(head[1]) is Column.NAME


# 종별 사이는 보통 빈칸 둘 이상인데, 요강 양식은 「남청소년부(중,고) 여청소년부(중,고)」처럼 괄호 뒤 한 칸만 띄웠다.
_KIND_GAP = re.compile(r"\s{2,}|(?<=\))\s+")
_TITLE_KIND = re.compile(r"단체전\s*/\s*([^)]+)\)")
# 인제 전국대회 양식은 팀 표 앞 「※ 단체전 ( 중년부 )」 한 줄에 종별을 적는다.
_NOTE_KIND = re.compile(r"단체전\s*\(\s*([^)]+?)\s*\)")


def team_category_from_title(text: str) -> str | None:
    """「참가신청서(단체전/초등/저학년부)」처럼 쪽 제목에 적힌 단체전 종별. 「팀별」 칸 없이 쪽마다 제목으로 나누는 양식이다."""
    match = _TITLE_KIND.search(text) or _NOTE_KIND.search(text)
    if match is None:
        return None
    kind = " ".join(part.strip() for part in match.group(1).split("/") if part.strip())
    return kind if parse_category(kind) is not None else None


def team_categories(rows: Sequence[Sequence[str]]) -> tuple[str, ...]:
    """단체전 표 앞의 「팀별 | 초등고학년 4~6학년」 표에 남은 종별 글들. 종별 표가 아니면 빈 tuple.

    고른 것 하나만 남기는 신청서가 많지만, 홍성수관처럼 팀 묶음(A팀 · A팀 · A팀) 순서대로 종별을 여럿 적기도 한다.
    """
    if len(rows) != 1 or len(rows[0]) != 2:
        return ()
    parts = tuple(part for part in _KIND_GAP.split(rows[0][1].strip()) if part)
    if not parts or any(parse_category(part) is None for part in parts):
        return ()
    return parts


@dataclass
class _Grid:
    labels: list[str] = field(default_factory=list)
    names: list[list[str]] = field(default_factory=list)


def _collect(rows: Sequence[Sequence[str]]) -> _Grid:
    grid = _Grid()
    for row in rows[1:]:
        label = row[0].strip()
        names = [cell.strip() for cell in row[1:] if cell.strip()]
        if label:
            grid.labels.append(label)
            grid.names.append(names)
        elif grid.names:
            grid.names[-1].extend(names)
    return grid


def _collect_columns(rows: Sequence[Sequence[str]]) -> _Grid:
    grid = _Grid()
    for column, label in enumerate(rows[0][1:], start=1):
        if not label.strip():
            continue
        grid.labels.append(label.strip())
        grid.names.append([row[column].strip() for row in rows[1:] if column < len(row) and row[column].strip()])
    return grid


def _grid_of(rows: Sequence[Sequence[str]]) -> _Grid:
    return _collect_columns(rows) if _is_column_grid(rows) else _collect(rows)


def grid_categories(rows: Sequence[Sequence[str]]) -> tuple[str, ...]:
    """개인전 표의 종별 글을 표 순서대로(이름이 없는 종별도). 알아볼 수 없는 글(「26명 참가」)은 뺀다."""
    return tuple(label for label in _grid_of(rows).labels if parse_category(label) is not None)


def parse_category_grid(rows: Sequence[Sequence[str]], dojang: str | None, source: str, table_no: int) -> TableParse:
    result = TableParse(recognized=True)
    grid = _grid_of(rows)
    parsed = [parse_category(label) for label in grid.labels]
    known = fill_missing_gender([category for category in parsed if category is not None])
    filled = iter(known)
    for label, names, category in zip(grid.labels, grid.names, parsed, strict=True):
        if category is None:
            if names:
                result.problems.append(f"{source}: 종별 「{label}」 을 알아볼 수 없어 {len(names)}명을 넣지 못했습니다.")
            continue
        category = next(filled)
        # 성별을 모르는 개인전 선수는 명단 화면이 신청서마다 묶어 「다시 요청하세요」로 알린다(roster_check).
        for index, name in enumerate(names, start=1):
            where = f"{source}#{table_no}-{label}-{index}"
            result.participants.append(_person(where, name, dojang or "", category, label))
    if not dojang and result.participants:
        result.problems.append(f"{source}: 「단체명」을 찾지 못해 도장이 비었습니다.")
    return result


def _kinds_per_group(kinds: Sequence[str], groups: int) -> list[str] | None:
    """팀 묶음마다의 종별. 종별 하나면 모두 그것, 묶음 수와 같으면 순서대로, 그 밖에는 알 수 없다(None)."""
    if len(kinds) == 1:
        return [kinds[0]] * groups
    if len(kinds) == groups:
        return list(kinds)
    return None


def parse_team_grid(
    rows: Sequence[Sequence[str]], kinds: Sequence[str], dojang: str | None, source: str, table_no: int
) -> TableParse:
    """kinds 는 표 앞 「팀별」 칸이나 쪽 제목의 종별 글이다. 팀이 그 글을 지녀 단체전 부문이 종별대로 만들어진다."""
    result = TableParse(recognized=True)
    groups = len(rows[0]) // TEAM_COLUMNS
    per_group = _kinds_per_group(kinds, groups)
    filled = any(cell.strip() for row in rows[1:] for cell in row[1::TEAM_COLUMNS])
    if per_group is None:
        if filled:
            result.problems.append(f"{source}: 단체전 종별(○ 표시)을 알아볼 수 없어 팀을 넣지 못했습니다.")
        return result
    head = rows[0]
    for group, start in enumerate(range(0, groups * TEAM_COLUMNS, TEAM_COLUMNS)):
        kind = per_group[group]
        category = parse_category(kind)
        if category is None:
            continue
        team_name = _compact(head[start]).removesuffix(TEAM_SUFFIX)
        members, positions = [], []
        for row_no, row in enumerate(rows[1:], start=1):
            name = row[start + 1].strip() if start + 1 < len(row) else ""
            if not name:
                continue
            where = f"{source}#{table_no}-{group}-{team_name}-{row_no}"
            result.participants.append(_person(where, name, dojang or "", category))
            members.append(where)
            # 자리를 이름과 함께 남긴다. 순서만 두면 중견 칸이 빈 팀은 주장이 중견 자리로 밀려 보인다.
            positions.append(_compact(row[start]))
        if members:
            # 한 신청서에 단체전 표가 종별마다 따로 있고 표마다 「A팀」이 있어, 표 번호까지 넣어야 팀이 겹치지 않는다.
            team_id = f"{source}#팀{table_no}-{group}-{dojang}-{team_name}"
            result.teams.append(Team(team_id, f"{dojang} {team_name}", dojang or "", tuple(members), kind, tuple(positions)))
    return result
