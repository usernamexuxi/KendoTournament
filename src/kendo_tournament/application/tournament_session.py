"""화면이 쓰는 단 하나의 창구. 대회 상태를 들고, 바꿀 때마다 대회 파일에 자동 저장한다."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from kendo_tournament.application.draw_brackets import draw_division, pending_changes, rebuild_divisions
from kendo_tournament.application.export_brackets import export_pages
from kendo_tournament.application.import_roster import ImportReport, ReaderFor, import_roster
from kendo_tournament.application.print_booklet import (
    booklet_page_numbers,
    booklet_pages,
    move_in_order,
    print_order,
    toggle_page_break,
)
from kendo_tournament.domain.division.builder import DivisionResult
from kendo_tournament.domain.division.category_table import CategoryTable
from kendo_tournament.domain.division.editing import merge_rules, split_rules
from kendo_tournament.domain.division.individual_categories import participant_category
from kendo_tournament.domain.draw.bracket import Bracket
from kendo_tournament.domain.draw.editing import insert_entry, recommend_insert_slots, swap_slots, withdraw
from kendo_tournament.domain.draw.validate import first_match_conflicts
from kendo_tournament.domain.layout.bracket_layout import PageLayout
from kendo_tournament.domain.model import Division, DivisionRule, Entry, Participant
from kendo_tournament.domain.ports import BracketExporter, TournamentRepository
from kendo_tournament.domain.tournament import Tournament
from kendo_tournament.domain.written_form import WrittenForm, WrittenRoster, written_roster

TOURNAMENT_EXTENSION = ".kendo"
_UNSAFE_FILENAME = re.compile(r'[\\/:*?"<>|]+')


class TournamentSession:
    def __init__(self, repository: TournamentRepository, reader_for: ReaderFor, save_dir: Path) -> None:
        self._repository = repository
        self._reader_for = reader_for
        self._save_dir = save_dir
        self.tournament = Tournament("새 대회")
        self.path: Path | None = None
        self.last_division_result: DivisionResult | None = None
        self.excluded_labels: set[str] = set()

    def new(self, name: str) -> None:
        self.tournament = Tournament(name.strip() or "새 대회")
        self.path = None
        self.last_division_result = None
        self._autosave()

    def open(self, path: Path) -> None:
        self.tournament = self._repository.load(path)
        self.path = path
        self.last_division_result = None

    def save_as(self, path: Path) -> None:
        self.path = path
        self._repository.save(self.tournament, path)

    @property
    def save_dir(self) -> Path:
        """대회 파일·뒤표지 로고·표지 사진 등을 두는 저장 폴더."""
        return self._save_dir

    def default_path(self) -> Path:
        safe = _UNSAFE_FILENAME.sub("_", self.tournament.name).strip() or "대회"
        return self._save_dir / f"{safe}{TOURNAMENT_EXTENSION}"

    def save_changes(self) -> None:
        """다른 모듈(책자 설정 등)이 대회를 고친 뒤 대회 파일에 남긴다."""
        self._autosave()

    def printable_labels(self) -> list[str]:
        """확인 화면에서 빼지 않았고 대진을 짠 부문을 인쇄 순서대로."""
        return [label for label in self.print_order() if label not in self.excluded_labels and label in self.tournament.brackets]

    def _autosave(self) -> None:
        if self.path is None:
            self.path = self.default_path()
        self._repository.save(self.tournament, self.path)

    def update_settings(self, **changes) -> None:
        for key, value in changes.items():
            if not hasattr(self.tournament, key):
                raise AttributeError(key)
            setattr(self.tournament, key, value)
        self._autosave()

    def import_files(self, paths: Sequence[Path]) -> ImportReport:
        """같은 파일을 다시 넣으면 그 파일에서 읽었던 명단을 새 내용으로 바꾼다."""
        report = import_roster(paths, self._reader_for)
        sources = {p.source for p in report.participants}
        kept = [p for p in self.tournament.participants if p.source not in sources]
        self.tournament.participants = kept + list(report.participants)
        team_sources = {t.id.split("#")[0] for t in report.teams}
        self.tournament.teams = [t for t in self.tournament.teams if t.id.split("#")[0] not in team_sources] + list(report.teams)
        self._autosave()
        return report

    def add_written_form(self, form: WrittenForm) -> WrittenRoster:
        """직접 적은 신청서를 명단에 넣는다. 같은 도장을 다시 적으면 그 도장의 직접 작성 명단을 새 내용으로 바꾼다.

        도장이 비었으면 아무것도 바꾸지 않고 problems 로 알린다.
        """
        roster = written_roster(form)
        if not form.dojang.strip():
            return roster
        kept = [p for p in self.tournament.participants if p.source != form.source]
        self.tournament.participants = kept + list(roster.participants)
        self.tournament.teams = [t for t in self.tournament.teams if t.id.split("#")[0] != form.source] + list(roster.teams)
        self._autosave()
        return roster

    def set_categories(self, table: CategoryTable) -> None:
        """대회 종별 표를 바꾼다. 알아볼 수 없는 종별 글이 있으면 ValueError — 그 줄로는 부문을 만들 수 없다."""
        unreadable = table.unreadable()
        if unreadable:
            raise ValueError(f"성별·학년을 알아볼 수 없는 종별이 있습니다: {', '.join(unreadable)}")
        self.tournament.categories = table
        self._autosave()

    def categories_in_file(self, path: Path) -> CategoryTable:
        """요강·신청서 파일 속 신청서 양식의 종별. 양식이 없으면 ValueError."""
        found = self._reader_for(path).read(path).form_categories
        if found is None:
            raise ValueError(f"{path.name} 에서 신청서 양식의 종별(「종 별」 표나 「팀별」 칸)을 찾지 못했습니다.")
        return found

    def set_participants(self, participants: list[Participant]) -> None:
        self.tournament.participants = participants
        self._autosave()

    def merge_dojangs(self, names: list[str], representative: str) -> None:
        self.tournament.merge_dojangs(names, representative)
        self._autosave()

    def set_rules(self, rules: list[DivisionRule]) -> DivisionResult:
        self.tournament.rules = rules
        self.last_division_result = rebuild_divisions(self.tournament)
        self._autosave()
        return self.last_division_result

    def merge_divisions(self, labels: Sequence[str]) -> DivisionResult:
        """나뉜 부문 여러 개를 하나로 합친다. 규칙을 고쳐 두므로 다시 나눠도 유지된다."""
        return self.merge_division_groups([labels])

    def merge_division_groups(self, groups: Sequence[Sequence[str]]) -> DivisionResult:
        """묶음마다 하나로 합친다(부전승 점검의 「추천 모두 합치기」). 묶음끼리는 겹치지 않아야 한다."""
        rules = self.tournament.rules
        for labels in groups:
            rules = merge_rules(rules, self._rule_ids_of(labels))
        return self.set_rules(rules)

    def split_divisions(self, labels: Sequence[str]) -> DivisionResult:
        """합쳐진 부문을 학년별로 나눈다. 혼자인 학년은 옆 학년과 다시 합쳐진다.

        신청서가 「1~2학년」처럼 범위로만 적은 선수가 있으면 ValueError — 나누면 그 선수들이 어느 학년에도 못 든다.
        """
        ranged = [
            person.name
            for label in labels
            for person in self._participants_in(label)
            if (category := participant_category(person)) and category.grade_from != category.grade_to
        ]
        if ranged:
            raise ValueError(
                f"신청서에 학년이 범위로만 적힌 선수({ranged[0]} 등 {len(ranged)}명)가 있어 학년별로 나눌 수 없습니다. "
                "나누려면 학년을 알아본 뒤 규칙 표에서 범위를 고쳐 주세요."
            )
        return self.set_rules(split_rules(self.tournament.rules, self._rule_ids_of(labels)))

    def _participants_in(self, label: str) -> list[Participant]:
        ids = {entry.id for entry in self.division(label).entries}
        return [person for person in self.tournament.participants if person.id in ids]

    def _rule_ids_of(self, labels: Sequence[str]) -> list[str]:
        return [rule_id for label in labels for rule_id in self.division(label).rule_ids]

    def refresh_divisions(self) -> DivisionResult:
        self.last_division_result = rebuild_divisions(self.tournament)
        self._autosave()
        return self.last_division_result

    def division(self, label: str) -> Division:
        for division in self.tournament.divisions:
            if division.label == label:
                return division
        raise KeyError(label)

    def bracket(self, label: str) -> Bracket | None:
        return self.tournament.brackets.get(label)

    def draw(self, label: str) -> Bracket:
        bracket = draw_division(self.tournament, self.division(label))
        self._autosave()
        return bracket

    def draw_missing(self) -> int:
        count = 0
        for division in self.tournament.divisions:
            if division.label not in self.tournament.brackets:
                draw_division(self.tournament, division)
                count += 1
        self._autosave()
        return count

    def _replace_bracket(self, label: str, bracket: Bracket) -> Bracket:
        self.tournament.brackets[label] = bracket
        self._autosave()
        return bracket

    def swap(self, label: str, i: int, j: int) -> Bracket:
        return self._replace_bracket(label, swap_slots(self._require(label), i, j))

    def withdraw(self, label: str, slot: int) -> Bracket:
        return self._replace_bracket(label, withdraw(self._require(label), slot))

    def insert(self, label: str, entry: Entry) -> Bracket:
        bracket = self._require(label)
        slots = recommend_insert_slots(bracket, entry, self.tournament.dojang_of)
        if not slots:
            raise ValueError("빈 자리(부전승 자리)가 없어 끼워 넣을 수 없습니다. 「다시 추첨」을 써야 합니다.")
        return self._replace_bracket(label, insert_entry(bracket, slots[0], entry))

    def set_title(self, label: str, title: str) -> Bracket:
        return self._replace_bracket(label, self._require(label).with_title(title))

    def conflicts(self, label: str) -> list[tuple[int, int]]:
        return first_match_conflicts(self._require(label), self.tournament.dojang_of)

    def pending(self, label: str) -> tuple[list[Entry], list[Entry]]:
        return pending_changes(self.tournament, self.division(label))

    def _require(self, label: str) -> Bracket:
        bracket = self.tournament.brackets.get(label)
        if bracket is None:
            raise KeyError(f"{label} 부문은 아직 대진을 짜지 않았습니다.")
        return bracket

    def print_pages(self, labels: Sequence[str], first_page: int = 1) -> list[PageLayout]:
        """저장할 때와 똑같은 책자 쪽들. 미리보기가 쓴다."""
        return booklet_pages(self.tournament, labels, first_page)

    def print_order(self) -> list[str]:
        return print_order(self.tournament)

    def page_numbers(self, labels: Sequence[str]) -> dict[str, int]:
        """고른 부문마다 책자의 몇 쪽에 실리는지."""
        return booklet_page_numbers(self.tournament, labels)

    def move_in_print(self, label: str, step: int) -> None:
        move_in_order(self.tournament, label, step)
        self._autosave()

    def toggle_page_break(self, label: str) -> None:
        toggle_page_break(self.tournament, label)
        self._autosave()

    def export(self, labels: Sequence[str], exporter: BracketExporter, path: Path) -> Path:
        return export_pages(self.print_pages(labels), exporter, path)

    def rename_participant(self, participant_id: str, **changes) -> None:
        self.tournament.participants = [
            replace(p, **changes) if p.id == participant_id else p for p in self.tournament.participants
        ]
        self._autosave()
