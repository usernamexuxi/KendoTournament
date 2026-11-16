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
