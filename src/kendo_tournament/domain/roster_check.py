"""선수 한 명의 명단 정보가 대진을 짜기에 충분한지 판단한다."""

from __future__ import annotations

from collections.abc import Sequence

from kendo_tournament.domain.division.grade import resolve_grade
from kendo_tournament.domain.model import Participant, Team

NAME_SEPARATOR = ", "


def missing_fields(person: Participant, mixed_team_member: bool = False) -> list[str]:
    """비었거나 판단할 수 없는 항목 이름. 빈 목록이면 부문에 넣을 수 있다.

    혼성 단체전 팀원은 성별이 없는 게 맞다(신청서 종별에 성별이 없다) — mixed_team_member 면 성별을 따지지 않는다.
    """
    missing = []
    if not person.name.strip():
        missing.append("이름")
    if not person.dojang.strip():
        missing.append("도장")
    if person.gender is None and not mixed_team_member:
        missing.append("성별")
    if resolve_grade(person) is None:
        missing.append("학년 또는 나이(8세 이상)")
    return missing


def team_member_ids(teams: Sequence[Team]) -> set[str]:
    return {member_id for team in teams for member_id in team.member_ids}


def missing_gender_requests(participants: Sequence[Participant], teams: Sequence[Team]) -> list[str]:
    """성별이 없는 개인전 선수를 신청서마다 묶은 알림 줄.

    개인전 신청서에는 성별이 늘 적혀 온다(운영자) — 없으면 보낸 곳이 빠뜨린 것이라 다시 받아야 한다.
    단체전 팀원은 팀 종별을 따르므로 여기서 빼고, 혼성 팀원의 빈 성별도 알리지 않는다.
    """
    in_team = team_member_ids(teams)
    grouped: dict[tuple[str, str], list[str]] = {}
    for person in participants:
        if person.gender is None and person.id not in in_team:
            grouped.setdefault((person.dojang, person.source), []).append(person.name)
    return [
        f"{dojang or '도장 모름'} ({source or '직접 입력'}): 개인전 선수 {len(names)}명의 성별이 없습니다 — "
        f"{NAME_SEPARATOR.join(names)}. 보낸 곳에 성별을 다시 알려 달라고 요청하세요."
        for (dojang, source), names in grouped.items()
    ]


def duplicate_check_requests(pairs: Sequence[tuple[Participant, Participant]]) -> list[str]:
    """중복 의심 쌍을 「서류에서 무엇을 확인할지」로 쓴 알림 줄. 프로그램 오류가 아니라 신청서 작성 실수를 잡는 용도다."""
    lines = []
    for first, second in pairs:
        where = [_entry_place(first), _entry_place(second)]
        if first.source == second.source:
            place = f"{first.source or '직접 입력'} 한 장에 {' · '.join(where)} 두 번"
        else:
            place = f"{first.source or '직접 입력'} · {second.source or '직접 입력'} 두 신청서에"
        lines.append(
            f"서류 확인: {first.dojang} 「{first.name}」이(가) {place} 적혀 있습니다. "
            "같은 사람이면 하나를 지우고, 다른 사람이면 그대로 두세요."
        )
    return lines


def _entry_place(person: Participant) -> str:
    return person.category or "종별 없음"
