"""확장자 → 리더 허용 목록. 목록에 없는 형식은 거부한다."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from kendo_tournament.domain.ports import RosterReader, UnsupportedFormat

LEGACY_WORD_MESSAGE = "옛 워드 형식(.doc)은 읽을 수 없습니다. 워드에서 「다른 이름으로 저장 → .docx」로 다시 저장해 주세요."


def _docx() -> RosterReader:
    from kendo_tournament.infrastructure.readers.docx_reader import DocxReader

    return DocxReader()


def _hwpx() -> RosterReader:
    from kendo_tournament.infrastructure.readers.hwpx_reader import HwpxReader

    return HwpxReader()


def _hwp() -> RosterReader:
    from kendo_tournament.infrastructure.readers.hwp_reader import HwpReader

    return HwpReader()


def _pdf() -> RosterReader:
    from kendo_tournament.infrastructure.readers.pdf_reader import PdfReader

    return PdfReader()


READERS: dict[str, Callable[[], RosterReader]] = {
    ".docx": _docx,
    ".hwpx": _hwpx,
    ".hwp": _hwp,
    ".pdf": _pdf,
}
ACCEPTED_EXTENSIONS = tuple(READERS)


def reader_for(path: Path) -> RosterReader:
    extension = path.suffix.lower()
    if extension == ".doc":
        raise UnsupportedFormat(LEGACY_WORD_MESSAGE)
    factory = READERS.get(extension)
    if factory is None:
        allowed = ", ".join(ACCEPTED_EXTENSIONS)
        raise UnsupportedFormat(f"「{path.name}」은(는) 읽을 수 없는 형식입니다. 읽을 수 있는 형식: {allowed}")
    return factory()
