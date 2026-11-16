"""대회 파일(.kendo, 내용은 JSON) 저장·불러오기. DB 없이 파일 하나가 대회 하나다."""

from __future__ import annotations

import json
import os
from pathlib import Path

from kendo_tournament.domain.tournament import Tournament
from kendo_tournament.infrastructure.storage.json_codec import (
    UnreadableTournamentFile,
    tournament_from_dict,
    tournament_to_dict,
)

FILE_EXTENSION = ".kendo"


class JsonTournamentRepository:
    def save(self, tournament: Tournament, path: Path) -> None:
        """임시 파일에 다 쓴 뒤 바꿔 끼운다. 저장 도중 꺼져도 이전 파일이 깨지지 않는다."""
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(tournament_to_dict(tournament), ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(temporary, path)

    def load(self, path: Path) -> Tournament:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise UnreadableTournamentFile(f"대회 파일을 열 수 없습니다: {path.name}") from error
        return tournament_from_dict(data)
