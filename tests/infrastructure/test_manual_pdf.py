import pdfplumber

from kendo_tournament.application.help_content import MANUAL_TITLE, SECTIONS
from kendo_tournament.infrastructure.exporters.manual_pdf import write_manual


def test_사용설명서_PDF_에_도움말의_모든_절과_줄이_들어간다(tmp_path):
    path = write_manual(tmp_path / "설명서.pdf")
    with pdfplumber.open(path) as pdf:
        text = "".join(page.extract_text() or "" for page in pdf.pages).replace("\n", "").replace(" ", "")
    expected = [MANUAL_TITLE] + [section.title for section in SECTIONS]
    expected += [line for section in SECTIONS for group in section.groups for line in group.lines]
    missing = [item for item in expected if item.replace(" ", "") not in text]
    assert not missing, missing[:3]


def test_설명서_그림은_단계마다_있고_단계_제목과_짝이_맞는다():
    """그림은 scripts/make_manual_shots.py 가 만든다. 단계 제목을 바꾸고 짝을 안 고치면 그림이 조용히 빠진다."""
    from kendo_tournament.application.help_content import SECTION_PICTURES, SECTIONS
    from kendo_tournament.infrastructure.exporters.manual_pdf import PICTURE_DIR

    titles = {section.title for section in SECTIONS}
    assert set(SECTION_PICTURES) <= titles
    assert all((PICTURE_DIR / name).is_file() for name in SECTION_PICTURES.values())


def test_그림이_없으면_설명서를_만들다_멈추고_알린다(tmp_path, monkeypatch):
    import pytest

    from kendo_tournament.infrastructure.exporters import manual_pdf

    monkeypatch.setattr(manual_pdf, "PICTURE_DIR", tmp_path / "없음")
    with pytest.raises(FileNotFoundError):
        manual_pdf.write_manual(tmp_path / "설명서.pdf")
