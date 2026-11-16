"""대진표 쪽을 만들고 파일로 내보낸다. pages_for 는 부문마다 한 장(대진 화면 미리보기용)이다."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from kendo_tournament.domain.draw.bracket import Bracket
from kendo_tournament.domain.draw.numbering import number_matches
from kendo_tournament.domain.layout.bracket_layout import PageLayout
from kendo_tournament.domain.layout.bracket_pages import layout_bracket
from kendo_tournament.domain.ports import BracketExporter


def pages_for(brackets: Sequence[Bracket]) -> list[PageLayout]:
    pages: list[PageLayout] = []
    for bracket in brackets:
        pages += layout_bracket(bracket, number_matches(bracket))
    return pages


def export_pages(pages: Sequence[PageLayout], exporter: BracketExporter, path: Path) -> Path:
    """만들어 둔 쪽들을 파일 하나로 저장한다."""
    if not pages:
        raise ValueError("내보낼 대진이 없습니다.")
    exporter.export(list(pages), path)
    return path
