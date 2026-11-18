"""⑥ 출력: 앞표지 → 대회사 → 끼워 넣은 문서 → 대회식순·임원·일정 → 대진표 → 뒤표지 를 한 묶음으로 만든다.

쪽 번호는 참고 책자처럼 대회식순 쪽을 1 로 시작한다(표지·대회사·끼운 문서는 번호 없음).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from kendo_tournament.application.export_brackets import export_pages
from kendo_tournament.application.tournament_session import TournamentSession
from kendo_tournament.domain.book import BookSettings, GreetingSource
from kendo_tournament.domain.greeting import Greeting
from kendo_tournament.domain.layout.booklet_sheet import number_pages
from kendo_tournament.domain.layout.greeting_page import greeting_page
from kendo_tournament.domain.layout.photo_cover_page import (
    PhotoCoverContent,
    photo_back_cover,
    photo_front_cover,
)
from kendo_tournament.domain.layout.primitives import PageLayout
from kendo_tournament.domain.layout.program_pages import program_pages
from kendo_tournament.domain.photo_cover import (
    EXAMPLE_PREFIX,
    CoverChoice,
    CoverLogo,
    PhotoCoverSettings,
    cover_title_lines,
)
from kendo_tournament.domain.ports import (
    BracketExporter,
    CoverDesignReader,
    CoverLogoStore,
    CoverPhotoLibrary,
    PageInserter,
    PhotoReader,
)
from kendo_tournament.domain.program import ProgramContent
from kendo_tournament.domain.tournament import Scope

BRACKET_WORD = "대진표"
PHOTO_FOLDER_NAME = "표지사진"
CATALOG_LABEL = "카탈로그"


@dataclass(frozen=True)
class CoverSources:
    """표지 재료: 따로 만들어 온 표지 파일을 읽는 곳, 사진을 읽는 곳, 뒤표지 로고, 배포본 표지 사진."""

    designs: CoverDesignReader
    photos: PhotoReader
    city_logo: CoverLogoStore
    library: CoverPhotoLibrary


class OutputBook:
    """책자 설정을 고치고(대회 파일에 저장), 찍을 쪽을 만든다."""

    def __init__(self, session: TournamentSession, inserter: PageInserter, cover: CoverSources) -> None:
        self._session = session
        self._inserter = inserter
        self._designs = cover.designs
        self._photos = cover.photos
        self._city_logo = cover.city_logo
        self._library = cover.library

    @property
    def settings(self) -> BookSettings:
        return self._session.tournament.book

    def _update(self, **changes) -> None:
        self._session.tournament.book = replace(self.settings, **changes)
        self._session.save_changes()

    def use_cover_file(self, path: Path) -> None:
        """따로 만들어 온 앞표지를 쓴다. 못 읽는 파일이면 InsertError 를 내고 설정은 그대로 둔다."""
        self._designs.page(path)
        self._update(cover_file=str(path))

    def stop_cover_file(self) -> None:
        """가져온 앞표지를 빼고 사진 표지로 돌아간다."""
        self._update(cover_file="")

    def add_inserts(self, paths: list[Path]) -> None:
        self._update(inserts=(*self.settings.inserts, *(str(path) for path in paths)))

    def remove_insert(self, index: int) -> None:
        inserts = list(self.settings.inserts)
        del inserts[index]
        self._update(inserts=tuple(inserts))

    def move_insert(self, index: int, step: int) -> None:
        inserts = list(self.settings.inserts)
        target = index + step
        if 0 <= target < len(inserts):
            inserts[index], inserts[target] = inserts[target], inserts[index]
            self._update(inserts=tuple(inserts))

    def file_stem(self) -> str:
        return f"{self._session.tournament.name} {BRACKET_WORD}"

    def pages(self) -> list[PageLayout]:
        """찍을 쪽 전부. 끼울 문서를 못 읽으면 InsertError, 사진·로고를 못 읽으면 ExportError, 대진이 없으면 ValueError."""
        program = program_pages(self.settings.program)
        first = len(program) + 1
        brackets = self._session.print_pages(self._session.printable_labels(), first)
        if not brackets:
            raise ValueError("찍을 대진이 없습니다. ⑤ 인쇄 순서에서 종별을 하나 이상 체크해 주세요.")
        inserted = [page for path in self.settings.inserts for page in self._inserter.pages(Path(path))]
        number_pages(program)
        front, back = self._front_cover(), self._back_cover()
        covers_front = [front] if front is not None else []
        covers_back = [back] if back is not None else []
        return [*covers_front, *self._greeting_pages(), *inserted, *program, *brackets, *covers_back]

    def is_national(self) -> bool:
        """전국 대회는 사진 표지를 쓰지 않고, 대회사 쪽을 고를 수 있다(운영자 지시)."""
        return self._session.tournament.scope is Scope.NATIONAL

    def greeting_source(self) -> GreetingSource:
        """광명 대회는 늘 프로그램 틀, 전국 대회는 고른 것(안 골랐으면 빼기)."""
        if not self.is_national():
            return GreetingSource.TEMPLATE
        return self.settings.greeting_source or GreetingSource.NONE

    def set_greeting_source(self, source: GreetingSource) -> None:
        """틀로 넣기·빼기. 파일로 넣기는 use_greeting_file 로 한다."""
        self._update(greeting_source=source)

    def use_greeting_file(self, path: Path) -> None:
        """받은 파일을 대회사 자리에 넣는다. 못 읽으면 InsertError 를 내고 설정은 그대로 둔다."""
        self._inserter.pages(path)
        self._update(greeting_source=GreetingSource.FILE, greeting_file=str(path))

    def _greeting_pages(self) -> list[PageLayout]:
        source = self.greeting_source()
        if source is GreetingSource.NONE:
            return []
        if source is GreetingSource.FILE:
            return self._inserter.pages(Path(self.settings.greeting_file))
        return [self.greeting_page()]

    def greeting_page(self) -> PageLayout:
        """대회사 쪽. 사진 파일을 못 읽으면 ExportError(옮겨졌으면 다시 고르라고 알린다)."""
        greeting = self.settings.greeting
        photo = self._photos.read(Path(greeting.photo_file)) if greeting.photo_file else None
        held = self._session.tournament.held_on
        date_text = greeting.date_text.strip() or (f"{held.year}. {held.month}. {held.day}" if held else "")
        return greeting_page(greeting, date_text, photo)

    def _photo_cover_content(self) -> PhotoCoverContent:
        photo_cover = self.settings.photo_cover
        tournament = self._session.tournament
        held = tournament.held_on
        date_text = photo_cover.date_text.strip() or (f"{held.year}.{held.month:02d}.{held.day:02d}" if held else "")
        credits = (("주최", photo_cover.host), ("주관", photo_cover.organizer), ("후원", photo_cover.sponsor))
        return PhotoCoverContent(
            tuple(cover_title_lines(photo_cover.title_lines, tournament.name)),
            date_text,
            photo_cover.venue.strip(),
            tuple((label, value.strip()) for label, value in credits if value.strip()),
        )

    def set_photo_cover(self, photo_cover: PhotoCoverSettings) -> None:
        """사진 표지 설정을 바꾼다(대회 파일에 저장). 고른 사진을 먼저 읽어 보고, 못 읽으면 ExportError 로 그대로 둔다."""
        front, back = chosen_photo(photo_cover.photo), chosen_photo(photo_cover.back_photo)
        if front is not None:
            self._photos.read_front_cover(front)
        if back is not None:
            self._photos.read_back_cover(back)
        self._update(photo_cover=photo_cover)

    def photo_folder(self) -> Path:
        """표지 사진을 모아 두는 폴더. 사진 고르기 창이 여기서 열린다."""
        return self._session.save_dir / PHOTO_FOLDER_NAME

    def cover_choice(self, front: bool) -> CoverChoice:
        """고르는 칸 맨 앞의 기본 사진: 카탈로그(빈 값)."""
        return CoverChoice(CATALOG_LABEL, "", self._library.catalog_front if front else self._library.catalog_back)

    def folder_choices(self) -> tuple[CoverChoice, ...]:
        """운영자 사진 폴더의 사진(앞·뒤 칸 모두에 보인다). 폴더를 못 열면 ExportError."""
        return self._library.folder_photos(self.photo_folder())

    def city_logo(self) -> CoverLogo | None:
        return self._city_logo.load()

    def choose_city_logo(self, path: Path) -> None:
        """뒤표지 왼쪽 아래 광명시 로고 그림을 저장 폴더에 넣는다. 못 읽으면 ExportError."""
        self._city_logo.replace(path)

    def set_greeting(self, greeting: Greeting) -> None:
        """대회사 내용을 바꾼다(대회 파일에 저장). 사진을 골랐으면 먼저 읽어 보고, 못 읽으면 ExportError 로 그대로 둔다."""
        if greeting.photo_file:
            self._photos.read(Path(greeting.photo_file))
        self._update(greeting=greeting)

    def _back_cover(self) -> PageLayout | None:
        """만들어 온 뒤표지 파일 → (전국 대회면 없음) → 고른 사진 + 카탈로그 아래쪽 로고들 → 카탈로그 뒤표지 그대로."""
        if self.settings.back_cover_file:
            return self._designs.page(Path(self.settings.back_cover_file))
        if self.is_national():
            return None
        back_photo = chosen_photo(self.settings.photo_cover.back_photo)
        if back_photo is None:
            # 카탈로그 뒤표지는 완성된 표지라 그늘·로고 없이 넣은 그대로 쓴다(표지 파일 넣기와 같은 길).
            return self._designs.page(self._library.catalog_back)
        back = self._photos.read_back_cover(back_photo)
        return photo_back_cover(back, self._city_logo.load(), self._library.tourism_badges())

    def use_back_cover_file(self, path: Path) -> None:
        """따로 만들어 온 뒤표지를 쓴다. 못 읽는 파일이면 InsertError 를 내고 설정은 그대로 둔다."""
        self._designs.page(path)
        self._update(back_cover_file=str(path))

    def stop_back_cover_file(self) -> None:
        self._update(back_cover_file="")

    def set_team_members(self, shown: bool) -> None:
        """단체전 대진표의 팀 상자 밑에 팀원 이름을 실을지 정한다(대회 파일에 저장)."""
        self._update(team_members=shown)

    def set_program(self, program: ProgramContent) -> None:
        """대회식순·대회임원·일정안내 내용을 바꾼다(대회 파일에 저장)."""
        self._update(program=program)

    def _front_cover(self) -> PageLayout | None:
        """만들어 온 앞표지 파일은 그대로, 전국 대회면 없음, 사진(안 골랐으면 카탈로그 사진)에 글을 얹는다."""
        if self.settings.cover_file:
            return self._designs.page(Path(self.settings.cover_file))
        if self.is_national():
            return None
        chosen = chosen_photo(self.settings.photo_cover.photo)
        photo = self._photos.read_front_cover(self._library.catalog_front if chosen is None else chosen)
        return photo_front_cover(self._photo_cover_content(), photo)

    def export(self, exporter: BracketExporter, path: Path) -> Path:
        return export_pages(self.pages(), exporter, path)


def chosen_photo(ref: str) -> Path | None:
    """설정에 적힌 표지 사진. 비었거나 예전 판의 배포본 예시(「예시:…」, 지금은 없음)면 None(카탈로그)."""
    if not ref or ref.startswith(EXAMPLE_PREFIX):
        return None
    return Path(ref)
