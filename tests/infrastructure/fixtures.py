"""시험용 신청서를 가짜 이름으로 만든다. 실제 신청서는 저장소에 넣지 않는다."""

from __future__ import annotations

from pathlib import Path

from docx import Document

HEADER = ("번호", "성 명", "성별", "학년", "나이")


def make_docx(path: Path, dojang: str, rows: list[tuple[str, ...]], header=HEADER, dojang_in_paragraph=True) -> Path:
    document = Document()
    document.add_paragraph("2026 광명시장배 검도대회 참가 신청서")
    if dojang_in_paragraph:
        document.add_paragraph(f"도장명 : {dojang}")
    table = document.add_table(rows=1, cols=len(header))
    for cell, text in zip(table.rows[0].cells, header, strict=True):
        cell.text = text
    for row in rows:
        cells = table.add_row().cells
        for cell, text in zip(cells, row, strict=True):
            cell.text = text
    document.save(str(path))
    return path
