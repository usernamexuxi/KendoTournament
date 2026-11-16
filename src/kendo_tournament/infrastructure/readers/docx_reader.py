"""워드(.docx) 신청서 리더."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from docx import Document
from docx.table import Table as DocxTable
from docx.text.paragraph import Paragraph as DocxParagraph

from kendo_tournament.domain.ports import ReadResult
from kendo_tournament.infrastructure.readers.document_text import Block, Paragraph, Table, blocks_to_result


def _unique_cells(row) -> tuple[str, ...]:
    """병합된 칸은 python-docx 가 같은 칸을 여러 번 돌려주므로 한 번만 쓴다."""
    texts, seen = [], set()
    for cell in row.cells:
        if id(cell._tc) in seen:
            continue
        seen.add(id(cell._tc))
        texts.append(cell.text.strip())
    return tuple(texts)


def docx_blocks(path: Path) -> Iterator[Block]:
    """워드 문서 본문의 문단과 표를 차례로."""
    document = Document(str(path))
    for item in document.iter_inner_content():
        if isinstance(item, DocxParagraph):
            yield Paragraph(item.text)
        elif isinstance(item, DocxTable):
            yield Table(tuple(_unique_cells(row) for row in item.rows))


class DocxReader:
    def read(self, path: Path) -> ReadResult:
        return blocks_to_result(docx_blocks(path), path.name)
