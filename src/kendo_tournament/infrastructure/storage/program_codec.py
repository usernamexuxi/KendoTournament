"""책자 앞쪽 내용(대회식순·임원·일정) ↔ JSON 사전. 나중에 생긴 칸이라 없는 예전 파일은 기본 틀로 읽는다."""

from __future__ import annotations

from typing import Any

from kendo_tournament.domain.program import DEFAULT_PROGRAM, ProgramContent, Row

ROW_FIELDS = ("opening", "closing", "officials", "schedule", "match_guide", "courts")
LINE_FIELDS = ("guide_notes", "court_rules")


def program_to_dict(program: ProgramContent) -> dict[str, Any]:
    data: dict[str, Any] = {name: [list(row) for row in getattr(program, name)] for name in ROW_FIELDS}
    data.update({name: list(getattr(program, name)) for name in LINE_FIELDS})
    return data


def program_from_dict(data: dict[str, Any] | None) -> ProgramContent:
    if data is None:
        return DEFAULT_PROGRAM
    rows: dict[str, tuple[Row, ...]] = {
        name: tuple((str(left), str(right)) for left, right in data.get(name, [])) for name in ROW_FIELDS
    }
    lines = {name: tuple(str(line) for line in data.get(name, [])) for name in LINE_FIELDS}
    return ProgramContent(**rows, **lines)
