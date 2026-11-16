"""사용설명서를 A4 PDF 로 만든다(운영자 지시: 워드 대신 PDF 내려받기). 글은 도움말 창과 같은 help_content 다."""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer

from kendo_tournament.application.help_content import MANUAL_TITLE, SECTIONS, HelpGroup, emphasized_parts
from kendo_tournament.infrastructure.exporters.pdf_exporter import BOLD, REGULAR, register_pdf_fonts

NAVY = HexColor("#0f3d80")
MUTED = HexColor("#4a5a70")
MARGIN = 18 * mm
BULLET_INDENT = 12


def _style(name: str, size: float, bold: bool = False, color=None, space_before: float = 0) -> ParagraphStyle:
    return ParagraphStyle(
        name,
        fontName=BOLD if bold else REGULAR,
        fontSize=size,
        leading=size * 1.55,
        textColor=color or HexColor("#14213d"),
        spaceBefore=space_before,
        spaceAfter=size * 0.4,
    )


TITLE = _style("title", 20, bold=True, color=NAVY)
SECTION = _style("section", 15, bold=True, color=NAVY, space_before=14)
SUMMARY = _style("summary", 10.5, color=MUTED)
GROUP = _style("group", 12, bold=True, space_before=6)
LINE = _style("line", 10.5)


def _marked_up(line: str) -> str:
    """「 」 안의 단추·칸 이름을 굵게. 글은 reportlab 마크업으로 읽히므로 먼저 이스케이프한다."""
    parts = []
    for text, bold in emphasized_parts(line):
        safe = escape(text)
        parts.append(f'<font name="{BOLD}">{safe}</font>' if bold else safe)
    return "".join(parts)


def _group(group: HelpGroup) -> list:
    items = [ListItem(Paragraph(_marked_up(line), LINE), leftIndent=BULLET_INDENT) for line in group.lines]
    return [
        Paragraph(escape(group.heading), GROUP),
        ListFlowable(items, bulletType="bullet", start="•", leftIndent=BULLET_INDENT),
    ]


def write_manual(path: Path) -> Path:
    """설명서를 path 에 쓴다. 글꼴이 없으면 FontMissing, 쓸 수 없으면 OSError."""
    register_pdf_fonts()
    story: list = [Paragraph(escape(MANUAL_TITLE), TITLE), Spacer(1, 4 * mm)]
    for section in SECTIONS:
        story += [Paragraph(escape(section.title), SECTION), Paragraph(escape(section.summary), SUMMARY)]
        for group in section.groups:
            story += _group(group)
    document = SimpleDocTemplate(
        str(path), pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN, bottomMargin=MARGIN, title=MANUAL_TITLE
    )
    document.build(story)
    return path
