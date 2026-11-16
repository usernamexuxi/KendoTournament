"""바깥(파일·저장소)과 맞닿는 인터페이스. infrastructure 가 구현하고 application 이 쓴다."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from kendo_tournament.domain.division.category_table import CategoryTable
from kendo_tournament.domain.greeting import Photo
from kendo_tournament.domain.layout.bracket_layout import PageLayout
from kendo_tournament.domain.model import Participant, Team
from kendo_tournament.domain.photo_cover import BackCoverPhoto, CoverChoice, CoverLogo

if TYPE_CHECKING:
    from kendo_tournament.domain.tournament import Tournament


@dataclass(frozen=True)
class ReadResult:
    """form_categories 는 문서 속 신청서 양식에 적힌 종별(개인전 종별 줄·단체전 「팀별」 칸). 양식이 없으면 None."""

    participants: tuple[Participant, ...]
    teams: tuple[Team, ...] = ()
    problems: tuple[str, ...] = field(default_factory=tuple)
    form_categories: CategoryTable | None = None


class TournamentFileError(Exception):
    """대회 파일을 열 수 없음. 메시지는 운영자에게 그대로 보여 준다."""


class ExportError(Exception):
    """대진표 파일을 만들 수 없음(글꼴 없음 등). 메시지는 운영자에게 그대로 보여 준다."""


class UnsupportedFormat(Exception):
    """허용 목록에 없는 파일 형식. 메시지는 운영자에게 그대로 보여 준다."""


class RosterReader(Protocol):
    def read(self, path: Path) -> ReadResult: ...


class InsertError(Exception):
    """책자에 끼워 넣을 문서를 읽을 수 없음. 메시지는 운영자에게 그대로 보여 준다."""


class PageInserter(Protocol):
    """파일 하나를 책자에 끼워 넣을 A4 쪽들로 바꾼다. 못 읽으면 InsertError."""

    def pages(self, path: Path) -> list[PageLayout]: ...


class CoverDesignReader(Protocol):
    """따로 만들어 온 앞표지 파일(PDF 첫 쪽 · 그림)을 A4 한 쪽으로. 못 읽으면 InsertError."""

    def page(self, path: Path) -> PageLayout: ...


class CoverLogoStore(Protocol):
    """뒤표지에 얹을 광명시 로고. 아직 없으면 None, 파일이 깨졌거나 형식이 틀리면 ExportError."""

    def load(self) -> CoverLogo | None: ...

    def replace(self, source: Path) -> None: ...


class PhotoReader(Protocol):
    """사진 파일을 읽는다(대회사 사진 · 표지 배경). 형식이 틀리거나 파일이 없으면 ExportError."""

    def read(self, path: Path) -> Photo: ...

    def read_front_cover(self, path: Path) -> Photo:
        """앞표지 배경용: A4 비율로 가운데를 잘라 온다. 글자 자리가 밝으면 흰 글자가 보이게 그 자리를 어둡게 눌러 온다."""
        ...

    def read_back_cover(self, path: Path) -> BackCoverPhoto:
        """뒤표지 배경용: A4 비율로 가운데를 잘라 오고, 로고 자리(왼쪽 아래)가 어두운지 함께 알려 준다."""
        ...


class CoverPhotoLibrary(Protocol):
    """배포본에 든 광명 기본 표지(카탈로그 앞·뒤표지), 뒤표지 관광 로고 묶음, 운영자 사진 폴더."""

    @property
    def catalog_front(self) -> Path: ...

    @property
    def catalog_back(self) -> Path: ...

    def tourism_badges(self) -> CoverLogo:
        """카탈로그 뒤표지 오른쪽 아래 관광 로고 묶음(투명 바탕 PNG). 없거나 깨졌으면 ExportError."""
        ...

    def folder_photos(self, folder: Path) -> tuple[CoverChoice, ...]:
        """운영자 사진 폴더의 사진(PNG·JPG). 폴더를 만들 수 없으면 ExportError."""
        ...


class BracketExporter(Protocol):
    def export(self, pages: list[PageLayout], path: Path) -> None: ...


class TournamentRepository(Protocol):
    def save(self, tournament: Tournament, path: Path) -> None: ...

    def load(self, path: Path) -> Tournament: ...
