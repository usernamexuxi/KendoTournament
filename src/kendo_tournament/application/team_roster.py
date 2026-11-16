"""단체전 대진표의 팀 상자 밑에 싣는 팀원 줄: 「선봉 홍길동 · 중견 김철수 · 주장 이영희」(자리 없는 팀은 이름만).

참고 책자(카탈로그)는 상자에 「도장+팀」만 쓰지만, 운영자가 팀 밑에 팀원 이름도 넣자고 했다(출력 화면에서 끌 수 있다).
"""

from __future__ import annotations

from collections.abc import Mapping

from kendo_tournament.domain.draw.bracket import Bracket
from kendo_tournament.domain.model import Team
from kendo_tournament.domain.tournament import Tournament

MEMBER_SEPARATOR = " · "
# 후보는 경기 순서 밖이라 신청서 어디에 적혔든 맨 끝에 둔다.
RESERVE = "후보"


def team_member_lines(tournament: Tournament, bracket: Bracket) -> dict[str, str]:
    """대진에 오른 팀 칸의 id → 팀원 줄. 개인전 칸이나 팀원이 없는 팀은 빠진다."""
    teams = {team.id: team for team in tournament.teams}
    names = {person.id: person.name for person in tournament.participants}
    lines = {}
    for entry in bracket.entries:
        team = teams.get(entry.id)
        if team is None:
            continue
        line = member_line(team, names)
        if line:
            lines[entry.id] = line
    return lines


def member_line(team: Team, names: Mapping[str, str]) -> str:
    """팀원 줄. 자리가 있으면 「자리 이름」, 후보는 맨 끝. 명단에서 지워진 팀원은 뺀다."""
    positions = team.positions if len(team.positions) == len(team.member_ids) else ("",) * len(team.member_ids)
    pairs = [(position, names[member]) for position, member in zip(positions, team.member_ids, strict=True) if member in names]
    ordered = [pair for pair in pairs if pair[0] != RESERVE] + [pair for pair in pairs if pair[0] == RESERVE]
    return MEMBER_SEPARATOR.join(f"{position} {name}" if position else name for position, name in ordered)
