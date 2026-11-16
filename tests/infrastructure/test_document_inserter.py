import pytest
from docx import Document

from kendo_tournament.domain.layout.document_pages import DocParagraph, document_pages
from kendo_tournament.domain.ports import InsertError
from kendo_tournament.infrastructure.exporters.pdf_exporter import PdfExporter
from kendo_tournament.infrastructure.inserts.document_inserter import DocumentInserter


def test_워드_문서는_글과_표를_쪽으로_옮긴다(tmp_path):
    path = tmp_path / "안내.docx"
    document = Document()
    document.add_paragraph("대회 운영 안내")
    table = document.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text, table.rows[0].cells[1].text = "개회식", "09:00"
    document.save(str(path))
    pages = DocumentInserter().pages(path)
    texts = [t.text for page in pages for t in page.texts]
    assert {"대회 운영 안내", "개회식", "09:00"} <= set(texts)


def test_PDF_는_쪽마다_그림으로_넣는다(tmp_path):
    source = tmp_path / "원본.pdf"
    PdfExporter().export(document_pages([DocParagraph("첫 쪽")]) * 2, source)
    pages = DocumentInserter().pages(source)
    assert len(pages) == 2
    assert all(len(page.images) == 1 and page.images[0].png.startswith(b"\x89PNG") for page in pages)


@pytest.mark.parametrize("name", ["a.txt", "a.xlsx", "a.doc"])
def test_허용하지_않는_형식은_거절한다(tmp_path, name):
    path = tmp_path / name
    path.write_bytes(b"x")
    with pytest.raises(InsertError, match="넣을 수 있는 파일"):
        DocumentInserter().pages(path)


def test_없는_파일과_깨진_파일은_알아듣게_알린다(tmp_path):
    with pytest.raises(InsertError, match="찾을 수 없습니다"):
        DocumentInserter().pages(tmp_path / "없음.pdf")
    broken = tmp_path / "깨짐.docx"
    broken.write_bytes(b"not a zip")
    with pytest.raises(InsertError, match="읽을 수 없는"):
        DocumentInserter().pages(broken)
