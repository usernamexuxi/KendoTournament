"""책자 표지와 대진표 사이에 끼울 문서를 A4 쪽으로 바꾼다.

PDF 는 쪽마다 그림으로 바꿔 원래 모양 그대로 싣는다(pdfplumber 와 함께 깔리는 pypdfium2 사용).
워드·한글은 글과 표만 꺼내 다시 앉힌다 — 원래 꾸밈은 한글·워드 프로그램 없이는 옮길 수 없다.
"""

from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path

import pypdfium2
from docx.opc.exceptions import PackageNotFoundError

from kendo_tournament.domain.layout.document_pages import DocBlock, DocParagraph, DocTable, document_pages
from kendo_tournament.domain.layout.primitives import PAGE_HEIGHT, PAGE_WIDTH, ImageItem, PageLayout
from kendo_tournament.domain.ports import InsertError
from kendo_tournament.infrastructure.readers.document_text import Block, Paragraph
from kendo_tournament.infrastructure.readers.docx_reader import docx_blocks
from kendo_tournament.infrastructure.readers.hwp_reader import HwpReadError, hwp_blocks
from kendo_tournament.infrastructure.readers.hwpx_reader import hwpx_blocks

INSERT_EXTENSIONS = (".pdf", ".docx", ".hwpx", ".hwp")
PDF_RENDER_SCALE = 2.0
POINTS_PER_MM = 72 / 25.4


def _to_doc_blocks(blocks: list[Block]) -> list[DocBlock]:
    return [DocParagraph(b.text) if isinstance(b, Paragraph) else DocTable(b.rows) for b in blocks]


def pdf_pages(path: Path) -> list[PageLayout]:
    """PDF 쪽을 그림으로 바꿔 A4 에 비율을 지켜 가운데 맞춘다."""
    pages = []
    document = pypdfium2.PdfDocument(str(path))
    try:
        for pdf_page in document:
            width_mm, height_mm = (size / POINTS_PER_MM for size in pdf_page.get_size())
            scale = min(PAGE_WIDTH / width_mm, PAGE_HEIGHT / height_mm)
            width, height = width_mm * scale, height_mm * scale
            buffer = BytesIO()
            pdf_page.render(scale=PDF_RENDER_SCALE).to_pil().save(buffer, format="PNG")
            image = ImageItem((PAGE_WIDTH - width) / 2, (PAGE_HEIGHT - height) / 2, width, height, buffer.getvalue())
            pages.append(PageLayout(images=[image]))
    finally:
        document.close()
    return pages


def _text_blocks(path: Path) -> list[Block]:
    extension = path.suffix.lower()
    if extension == ".docx":
        return list(docx_blocks(path))
    if extension == ".hwpx":
        return hwpx_blocks(path)
    return hwp_blocks(path)


class DocumentInserter:
    def pages(self, path: Path) -> list[PageLayout]:
        extension = path.suffix.lower()
        if extension not in INSERT_EXTENSIONS:
            allowed = ", ".join(INSERT_EXTENSIONS)
            raise InsertError(f"{path.name}: 넣을 수 있는 파일은 {allowed} 입니다.")
        if not path.exists():
            raise InsertError(f"{path.name}: 파일을 찾을 수 없습니다. 옮겼거나 지웠는지 확인해 주세요.")
        try:
            if extension == ".pdf":
                return pdf_pages(path)
            pages = document_pages(_to_doc_blocks(_text_blocks(path)))
        except (OSError, ValueError, zipfile.BadZipFile, PackageNotFoundError, HwpReadError, pypdfium2.PdfiumError) as error:
            raise InsertError(f"{path.name}: 읽을 수 없는 파일입니다 ({error}).") from error
        if not pages:
            raise InsertError(f"{path.name}: 넣을 글이나 표가 없습니다.")
        return pages
