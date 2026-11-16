"""대회 하나의 전체 상태. 대회 파일 하나에 이것이 통째로 저장된다."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from kendo_tournament.domain.book import BookSettings
from kendo_tournament.domain.division.category_table import DEFAULT_CATEGORY_TABLE, CategoryTable
from kendo_tournament.domain.division.dojang import dojang_key
from kendo_tournament.domain.draw.bracket import Bracket
from kendo_tournament.domain.model import Division, DivisionRule, Entry, Participant, Team


class Scope(Enum):
    NATIONAL = "전국"
    GWANGMYEONG = "광명"


@dataclass
class Tournament:
    name: str
    held_on: date | None = None
    scope: Scope = Scope.GWANGMYEONG
    participants: list[Participant] = field(default_factory=list)
    teams: list[Team] = field(default_factory=list)
    dojang_aliases: dict[str, str] = field(default_factory=dict)
    rules: list[DivisionRule] = field(default_factory=list)
    divisions: list[Division] = field(default_factory=list)
    brackets: dict[str, Bracket] = field(default_factory=dict)
    print_order: list[str] = field(default_factory=list)
    page_breaks: list[str] = field(default_factory=list)
    book: BookSettings = field(default_factory=BookSettings)
    categories: CategoryTable = DEFAULT_CATEGORY_TABLE

    def dojang_of(self, entry: Entry) -> str:
        return dojang_key(entry.dojang, self.dojang_aliases)

    def dojang_names(self) -> list[str]:
        """명단에 나온 도장 이름(공백 정리 전 원래 표기)을 중복 없이."""
        seen: dict[str, None] = {}
        for person in self.participants:
            seen.setdefault(person.dojang, None)
        return list(seen)

    def merge_dojangs(self, names: list[str], representative: str) -> None:
        """표기가 다른 같은 도장을 하나로 묶는다."""
        target = dojang_key(representative)
        for name in names:
            key = dojang_key(name)
            if key != target:
                self.dojang_aliases[key] = target

    def duplicate_people(self) -> list[tuple[Participant, Participant]]:
        """같은 도장·같은 이름이 두 번 나온 쌍. 지울지는 운영자가 정한다.

        신청서는 같은 사람을 개인전 표와 단체전 표에 함께 적는다. 개인전 선수와 단체전 팀원은 따로 세어,
        개인전끼리·팀원끼리 겹칠 때만 의심한다(운영자: 「같은 파일인데 왜 중복 의심이 뜨냐」).
        한 신청서가 같은 이름을 두 종별에 적은 것도 작성 실수일 수 있어 의심한다 — 이 검사는 서류 실수를 잡으려고 둔다.
        """
        team_members = {member for team in self.teams for member in team.member_ids}
        seen: dict[tuple[str, str, bool], Participant] = {}
        pairs = []
        for person in self.participants:
            key = (dojang_key(person.dojang, self.dojang_aliases), person.name.strip(), person.id in team_members)
            if key in seen:
                pairs.append((seen[key], person))
            else:
                seen[key] = person
        return pairs
