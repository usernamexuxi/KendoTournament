"""대회 상태 ↔ JSON 사전. 파일 구조가 바뀌면 FORMAT_VERSION 을 올리고 불러오기에서 옛 형식을 변환한다."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Any

from kendo_tournament.domain.book import BookSettings, GreetingSource
from kendo_tournament.domain.division.category_table import DEFAULT_CATEGORY_TABLE, CategoryTable
from kendo_tournament.domain.draw.bracket import Bracket
from kendo_tournament.domain.greeting import DEFAULT_GREETING, Greeting
from kendo_tournament.domain.model import (
    Division,
    DivisionRule,
    Entry,
    Event,
    Gender,
    Grade,
    Participant,
    Team,
)
from kendo_tournament.domain.photo_cover import PhotoCoverSettings
from kendo_tournament.domain.ports import TournamentFileError
from kendo_tournament.domain.tournament import Scope, Tournament
from kendo_tournament.infrastructure.storage.program_codec import program_from_dict, program_to_dict

FORMAT_VERSION = 1
# 「경기도」 범위는 고를 수 있다가 없어졌다(사용자 지시). 범위는 표시용이라 그때 저장한 파일은 광명으로 연다.
_RETIRED_SCOPES = {"GYEONGGI": Scope.GWANGMYEONG}


class UnreadableTournamentFile(TournamentFileError):
    pass


def _enum_name(value) -> str | None:
    return value.name if value is not None else None


def _scope(name: str) -> Scope:
    return _RETIRED_SCOPES.get(name) or Scope[name]


def _grade_value(grade: Grade | None) -> int | None:
    return grade.value if grade is not None else None


def _entry(entry: Entry | None) -> dict[str, str] | None:
    if entry is None:
        return None
    return {"id": entry.id, "name": entry.name, "dojang": entry.dojang, "team": entry.team}


def tournament_to_dict(t: Tournament) -> dict[str, Any]:
    return {
        "format_version": FORMAT_VERSION,
        "name": t.name,
        "held_on": t.held_on.isoformat() if t.held_on else None,
        "scope": t.scope.name,
        "participants": [
            {
                "id": p.id,
                "name": p.name,
                "gender": _enum_name(p.gender),
                "dojang": p.dojang,
                "grade": _grade_value(p.grade),
                "age": p.age,
                "region": p.region,
                "source": p.source,
                "category": p.category,
            }
            for p in t.participants
        ],
        "teams": [
            {
                "id": tm.id,
                "name": tm.name,
                "dojang": tm.dojang,
                "member_ids": list(tm.member_ids),
                "category": tm.category,
                "positions": list(tm.positions),
            }
            for tm in t.teams
        ],
        "dojang_aliases": dict(t.dojang_aliases),
        "rules": [
            {
                "id": r.id,
                "event": r.event.name,
                "gender": _enum_name(r.gender),
                "grade_from": r.grade_from.value,
                "grade_to": r.grade_to.value,
                "team_size": r.team_size,
                "min_entries": r.min_entries,
                "age_from": r.age_from,
                "age_to": r.age_to,
                "age_name": r.age_name,
            }
            for r in t.rules
        ],
        "divisions": [
            {"rule_ids": list(d.rule_ids), "label": d.label, "event": d.event.name, "entries": [_entry(e) for e in d.entries]}
            for d in t.divisions
        ],
        "brackets": {
            key: {"title": b.title, "seed": b.seed, "slots": [_entry(e) for e in b.slots]} for key, b in t.brackets.items()
        },
        "print_order": list(t.print_order),
        "page_breaks": list(t.page_breaks),
        "categories": {"individual": list(t.categories.individual), "team": list(t.categories.team)},
        "book": {
            "inserts": list(t.book.inserts),
            "cover_file": t.book.cover_file,
            "back_cover_file": t.book.back_cover_file,
            "greeting_source": t.book.greeting_source.name if t.book.greeting_source else None,
            "greeting_file": t.book.greeting_file,
            "program": program_to_dict(t.book.program),
            "team_members": t.book.team_members,
            "greeting": asdict(t.book.greeting),
            "photo_cover": asdict(t.book.photo_cover),
        },
    }


def _to_entry(data: dict[str, str] | None, team_ids: frozenset[str]) -> Entry | None:
    """팀 표시(team)가 생기기 전 파일은 팀 칸에도 표시가 없다. 그래서 대회의 팀 목록에 있는 칸은 팀으로 읽는다."""
    if data is None:
        return None
    is_team = bool(data.get("team", False)) or data["id"] in team_ids
    return Entry(data["id"], data["name"], data["dojang"], is_team)


def _optional(enum_type, name):
    return enum_type[name] if name is not None else None


def _optional_grade(value: int | None) -> Grade | None:
    return Grade(value) if value is not None else None


def _categories(data: dict[str, Any] | None) -> CategoryTable:
    """대회 종별 표는 나중에 생겼다. 그 전 파일은 그때 고정값이던 광명 회장기 종별로 읽는다."""
    if data is None:
        return DEFAULT_CATEGORY_TABLE
    return CategoryTable(tuple(data["individual"]), tuple(data["team"]))


def _book(data: dict[str, Any] | None) -> BookSettings:
    """책자 설정은 나중에 생겼다. 그 전에 저장한 파일에는 없으므로 기본값으로 읽는다.

    예전 디자인 표지 설정(title·color·cover_seed·accent·third)은 디자인 표지를 없애면서 읽지 않는다.
    """
    if data is None:
        return BookSettings()
    # 아래 칸들은 책자 설정보다 늦게 생겼다. 없으면 그 기능이 생기기 전의 동작(빈 값·기본 틀)으로 읽는다.
    team_members = bool(data.get("team_members", True))
    greeting = Greeting(**data["greeting"]) if "greeting" in data else DEFAULT_GREETING
    photo_cover = PhotoCoverSettings(**data["photo_cover"]) if "photo_cover" in data else PhotoCoverSettings()
    source = data.get("greeting_source")
    return BookSettings(
        tuple(data["inserts"]),
        data.get("cover_file", ""),
        data.get("back_cover_file", ""),
        program_from_dict(data.get("program")),
        team_members,
        greeting,
        photo_cover,
        GreetingSource[source] if source else None,
        data.get("greeting_file", ""),
    )


def tournament_from_dict(data: dict[str, Any]) -> Tournament:
    version = data.get("format_version")
    if version != FORMAT_VERSION:
        raise UnreadableTournamentFile(f"이 프로그램이 모르는 대회 파일 형식입니다(버전 {version}).")
    try:
        team_ids = frozenset(tm["id"] for tm in data["teams"])
        return Tournament(
            name=data["name"],
            held_on=date.fromisoformat(data["held_on"]) if data["held_on"] else None,
            scope=_scope(data["scope"]),
            participants=[
                Participant(
                    p["id"],
                    p["name"],
                    _optional(Gender, p["gender"]),
                    p["dojang"],
                    _optional_grade(p["grade"]),
                    p["age"],
                    p["region"],
                    p["source"],
                    # 개인전 종별은 나중에 생겼다. 그 전 파일의 선수는 종별 없이 읽고 학년으로 부문을 찾는다.
                    p.get("category", ""),
                )
                for p in data["participants"]
            ],
            # 팀 종별(category)·자리(positions)는 나중에 생겼다. 그 전 파일의 팀은 종별 없이 읽고(팀원 성별·학년으로
            # 부문을 찾는다), 자리 없이 읽는다(팀원 줄에 이름만 나온다).
            teams=[
                Team(
                    tm["id"],
                    tm["name"],
                    tm["dojang"],
                    tuple(tm["member_ids"]),
                    tm.get("category", ""),
                    tuple(tm.get("positions", ())),
                )
                for tm in data["teams"]
            ],
            dojang_aliases=dict(data["dojang_aliases"]),
            rules=[
                DivisionRule(
                    r["id"],
                    Event[r["event"]],
                    _optional(Gender, r["gender"]),
                    Grade(r["grade_from"]),
                    Grade(r["grade_to"]),
                    r["team_size"],
                    r["min_entries"],
                    r.get("age_from"),
                    r.get("age_to"),
                    r.get("age_name", ""),
                )
                for r in data["rules"]
            ],
            divisions=[
                Division(tuple(d["rule_ids"]), d["label"], Event[d["event"]], tuple(_to_entry(e, team_ids) for e in d["entries"]))
                for d in data["divisions"]
            ],
            brackets={
                key: Bracket(b["title"], tuple(_to_entry(e, team_ids) for e in b["slots"]), b["seed"])
                for key, b in data["brackets"].items()
            },
            # 인쇄 순서·새 쪽 설정은 나중에 생겼다. 그 전에 저장한 파일에는 없으므로 비어 있는 것으로 읽는다.
            print_order=list(data.get("print_order", [])),
            page_breaks=list(data.get("page_breaks", [])),
            book=_book(data.get("book")),
            categories=_categories(data.get("categories")),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise UnreadableTournamentFile(f"대회 파일이 손상되었습니다: {type(error).__name__} {error}") from error
