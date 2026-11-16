"""부문을 나누고 부문마다 대진을 추첨한다."""

from __future__ import annotations

import secrets

from kendo_tournament.domain.division.builder import DivisionResult, build_divisions
from kendo_tournament.domain.draw.bracket import Bracket
from kendo_tournament.domain.draw.draw import draw_bracket
from kendo_tournament.domain.model import Division, Entry
from kendo_tournament.domain.tournament import Tournament

SEED_BITS = 31


def rebuild_divisions(tournament: Tournament) -> DivisionResult:
    """부문을 다시 나눈다. 이미 짠 대진은 지우지 않는다.

    명단이 바뀌어 대진과 부문 출전자가 달라지면 pending_changes 로 보여 주고,
    운영자가 빼기·끼워 넣기로 반영한다(손으로 고친 대진을 지키기 위해서다).
    """
    result = build_divisions(tournament.participants, tournament.teams, tournament.rules)
    tournament.divisions = list(result.divisions)
    labels = {division.label for division in tournament.divisions}
    tournament.brackets = {label: b for label, b in tournament.brackets.items() if label in labels}
    return result


def pending_changes(tournament: Tournament, division: Division) -> tuple[list[Entry], list[Entry]]:
    """(대진에 아직 없는 출전자, 부문에서 빠졌는데 대진에 남은 출전자)."""
    bracket = tournament.brackets.get(division.label)
    if bracket is None:
        return [], []
    in_bracket = {e.id for e in bracket.entries}
    in_division = {e.id for e in division.entries}
    added = [e for e in division.entries if e.id not in in_bracket]
    removed = [e for e in bracket.entries if e.id not in in_division]
    return added, removed


def draw_division(tournament: Tournament, division: Division, seed: int | None = None) -> Bracket:
    """seed 를 주지 않으면 새로 뽑는다. 같은 seed 면 같은 대진이 나온다."""
    chosen = seed if seed is not None else secrets.randbits(SEED_BITS)
    bracket = draw_bracket(division.entries, division.label, chosen, tournament.dojang_of)
    previous = tournament.brackets.get(division.label)
    if previous is not None:
        bracket = bracket.with_title(previous.title)
    tournament.brackets[division.label] = bracket
    return bracket


def draw_all(tournament: Tournament) -> list[Bracket]:
    return [draw_division(tournament, division) for division in tournament.divisions]
