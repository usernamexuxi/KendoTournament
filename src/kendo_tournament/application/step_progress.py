"""왼쪽 단계 목록에 붙는 진행 표시와 아래 줄의 저장 알림 글.

쓰는 분이 컴퓨터에 익숙하지 않은 운영자라, 어느 단계를 끝냈고 다음이 무엇인지 화면이 먼저 알려 줘야 한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from kendo_tournament.domain.tournament import Tournament

DONE = "✓"


@dataclass(frozen=True)
class StepNote:
    """단계 이름 밑에 작게 붙는 글. done 이면 앞에 ✓ 를 붙인다."""

    text: str
    done: bool

    def __str__(self) -> str:
        return f"{DONE} {self.text}" if self.done else self.text


# 아직 안 한 단계는 단계 이름만 둔다. 「할 차례」를 붙였더니 운영자가 「그냥 선수 명단이라고 해」라고 했다.
NOT_YET = StepNote("", False)


def step_notes(tournament: Tournament) -> tuple[StepNote, ...]:
    """① 대회 정보 ~ ⑥ 책자 만들기 순서대로. 아직 안 했거나 확인할 거리가 없는 단계는 빈 글이다."""
    divisions = tournament.divisions
    drawn = sum(1 for division in divisions if division.label in tournament.brackets)
    roster = StepNote(f"{len(tournament.participants)}명", True) if tournament.participants else NOT_YET
    grouped = StepNote(f"종별 {len(divisions)}개", True) if divisions else NOT_YET
    if drawn and drawn == len(divisions):
        bracket = StepNote(f"{drawn}개 다 짬", True)
    elif drawn:
        bracket = StepNote(f"{drawn}/{len(divisions)}개 짬", False)
    else:
        bracket = NOT_YET
    return (StepNote(tournament.name, True), roster, grouped, bracket, NOT_YET, NOT_YET)


def saved_text(saved_at: datetime | None, file_name: str, opened: bool) -> str:
    """아래 줄 알림. 파일 경로 대신 저장 시각과 파일 이름만 보여 준다(경로는 운영자에게 낯설다).

    opened 는 이번에 바꾼 것 없이 저장된 파일을 열어 둔 상태다.
    """
    if saved_at is None:
        if opened:
            return f"「{file_name}」 열어 둠 — 바꾸면 바로 자동 저장됩니다"
        return f"아직 저장 전 — 무엇이든 바꾸면 「{file_name}」(으)로 저장됩니다"
    hour = saved_at.hour % 12 or 12
    noon = "오전" if saved_at.hour < 12 else "오후"
    return f"{DONE} 자동 저장됨 · {noon} {hour}:{saved_at.minute:02d} · {file_name}"
