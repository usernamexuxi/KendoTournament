"""형식별 리더가 공통으로 넘기는 「문단과 표의 흐름」을 명단으로 모은다."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from kendo_tournament.domain.division.category_table import CategoryTable
from kendo_tournament.domain.ports import ReadResult
from kendo_tournament.infrastructure.readers.category_form import (
    grid_categories,
    is_category_grid,
    is_team_grid,
    parse_category_grid,
    parse_team_grid,
    team_categories,
    team_category_from_title,
)
from kendo_tournament.infrastructure.readers.schedule_categories import court_categories, is_court_table
from kendo_tournament.infrastructure.readers.table_rows import (
    TableParse,
    dojang_from_text,
    dojang_in_rows,
    parse_table,
)


@dataclass(frozen=True)
class Paragraph:
    text: str


@dataclass(frozen=True)
class Table:
    rows: tuple[tuple[str, ...], ...]


Block = Paragraph | Table


def blocks_to_result(blocks: Iterable[Block], source: str) -> ReadResult:
    """표 앞 문단이나 명단이 아닌 표(도장 정보 표)에 나온 도장명은 그 뒤 명단 표의 기본 도장명이 된다."""
    participants, teams, problems = [], [], []
    context_dojang: str | None = None
    table_no = 0
    recognized = False
    team_kinds: tuple[str, ...] = ()
    found = _FormCategories()
    for block in blocks:
        if isinstance(block, Paragraph):
            context_dojang = dojang_from_text(block.text) or context_dojang
            title_kind = team_category_from_title(block.text)
            team_kinds = (title_kind,) if title_kind else team_kinds
            found.add_team(team_kinds if title_kind else ())
            continue
        table_no += 1
        if is_court_table(block.rows):
            found.add_schedule(*court_categories(block.rows))
            continue
        if is_category_grid(block.rows):
            found.add_individual(grid_categories(block.rows))
        parsed = _parse(block.rows, context_dojang, team_kinds, source, table_no)
        recognized = recognized or parsed.recognized
        if not parsed.recognized:
            context_dojang = dojang_in_rows(block.rows) or context_dojang
            team_kinds = team_categories(block.rows) or team_kinds
            found.add_team(team_categories(block.rows))
        participants += parsed.participants
        teams += parsed.teams
        problems += parsed.problems
    if not recognized:
        problems.append(f"{source}: 「이름」 머리글이 있는 표를 찾지 못했습니다. 명단 화면에서 직접 입력해 주세요.")
    return ReadResult(tuple(participants), tuple(teams), tuple(problems), found.table())


@dataclass
class _FormCategories:
    """문서 속 신청서 양식에 나온 종별을 처음 나온 순서대로 모은다(여러 쪽에 같은 종별이 되풀이돼도 한 번).

    신청서 양식이 없는 경기일정 문서는 「경기장배치」 표의 부문을 대신 쓴다(schedule_*).
    """

    individual: list[str] = field(default_factory=list)
    team: list[str] = field(default_factory=list)
    schedule_individual: list[str] = field(default_factory=list)
    schedule_team: list[str] = field(default_factory=list)

    def add_schedule(self, individual: Iterable[str], team: Iterable[str]) -> None:
        self.schedule_individual += [label for label in individual if label not in self.schedule_individual]
        self.schedule_team += [label for label in team if label not in self.schedule_team]

    def add_individual(self, labels: Iterable[str]) -> None:
        self.individual += [label for label in labels if label not in self.individual]

    def add_team(self, labels: Iterable[str]) -> None:
        self.team += [label for label in labels if label not in self.team]

    def table(self) -> CategoryTable | None:
        if self.individual or self.team:
            return CategoryTable(tuple(self.individual), tuple(self.team))
        if self.schedule_individual or self.schedule_team:
            return CategoryTable(tuple(self.schedule_individual), tuple(self.schedule_team))
        return None


def _parse(rows, dojang: str | None, team_kinds: tuple[str, ...], source: str, table_no: int) -> TableParse:
    """표 모양에 맞는 해석기를 고른다: 「종별 × 성명」 표, 「A팀 | 성명」 표, 그 밖에는 머리글(이름·성별…) 표."""
    if is_category_grid(rows):
        return parse_category_grid(rows, dojang, source, table_no)
    if is_team_grid(rows):
        return parse_team_grid(rows, team_kinds, dojang, source, table_no)
    return parse_table(rows, dojang, source, table_no)
