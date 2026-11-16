"""PDF 신청서 리더. 글자가 들어 있는 PDF 만 읽는다(스캔본은 오지 않는다는 개발자 답변)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pdfplumber

from kendo_tournament.domain.ports import ReadResult
from kendo_tournament.infrastructure.readers.document_text import Block, Paragraph, Table, blocks_to_result

SCANNED_MESSAGE = "{name}: 글자가 없는 PDF(스캔·팩스)라 읽을 수 없습니다. 명단 화면에서 직접 입력해 주세요."


def _blocks(pdf) -> Iterator[Block]:
    for page in pdf.pages:
        for line in (page.extract_text() or "").splitlines():
            yield Paragraph(line)
        for table in page.extract_tables():
            yield Table(tuple(tuple((cell or "").replace("\n", " ") for cell in row) for row in table))


class PdfReader:
    def read(self, path: Path) -> ReadResult:
        with pdfplumber.open(str(path)) as pdf:
            if not any(page.chars for page in pdf.pages):
                return ReadResult((), (), (SCANNED_MESSAGE.format(name=path.name),))
            blocks = list(_blocks(pdf))
        return blocks_to_result(blocks, path.name)
