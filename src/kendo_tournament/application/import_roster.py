"""신청 문서 여러 개를 읽어 하나의 명단으로 모은다."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from kendo_tournament.domain.model import Participant, Team
from kendo_tournament.domain.ports import RosterReader, UnsupportedFormat

ReaderFor = Callable[[Path], RosterReader]


@dataclass(frozen=True)
class ImportReport:
    participants: tuple[Participant, ...]
    teams: tuple[Team, ...]
    problems: tuple[str, ...]
    rejected: tuple[str, ...]


def import_roster(paths: Sequence[Path], reader_for: ReaderFor) -> ImportReport:
    """읽지 못한 파일은 건너뛰고 이유를 rejected 에 담는다. 읽은 칸의 문제는 problems 에 담는다."""
    participants: list[Participant] = []
    teams: list[Team] = []
    problems: list[str] = []
    rejected: list[str] = []
    for path in paths:
        try:
            result = reader_for(path).read(path)
        except UnsupportedFormat as error:
            rejected.append(str(error))
            continue
        # 신청서는 밖에서 온 파일이라 손상 형태를 다 알 수 없다. 한 파일이 깨졌다고 나머지 문서까지 못 읽으면 안 되므로
        # 넓게 잡되 삼키지 않고, 파일 이름과 함께 rejected 로 운영자에게 보여 준다.
        except Exception as error:  # noqa: BLE001
            rejected.append(f"{path.name}: 파일을 여는 중 문제가 생겼습니다 ({type(error).__name__}).")
            continue
        participants += result.participants
        teams += result.teams
        problems += result.problems
    return ImportReport(tuple(participants), tuple(teams), tuple(problems), tuple(rejected))
