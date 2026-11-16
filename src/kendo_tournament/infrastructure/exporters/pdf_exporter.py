"""PageLayout 을 A4 PDF 로 그린다."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from kendo_tournament.domain.layout.primitives import BASELINE_SHIFT, Align, Face, PageLayout, TextItem
from kendo_tournament.infrastructure.exporters.fonts import require_fonts

REGULAR = "MalgunGothic"
BOLD = "MalgunGothicBold"
TITLE = "CoverTitle"
LINE_COLOR = (0.15, 0.15, 0.15)


def register_pdf_fonts() -> None:
    """PDF 에 쓸 글꼴을 reportlab 에 한 번만 등록한다. 글꼴 파일이 없으면 FontMissing."""
    if REGULAR in pdfmetrics.getRegisteredFontNames():
        return
    regular, bold, title = require_fonts()
    pdfmetrics.registerFont(TTFont(REGULAR, str(regular)))
    pdfmetrics.registerFont(TTFont(BOLD, str(bold)))
    pdfmetrics.registerFont(TTFont(TITLE, str(title)))


def _font_name(item: TextItem) -> str:
    if item.face is Face.TITLE:
        return TITLE
    return BOLD if item.bold else REGULAR


def fitted_size(item: TextItem, font: str) -> float:
    """최대 너비를 넘는 글자는 넘지 않을 때까지 줄인다."""
    if item.max_width is None:
        return item.size_pt
    width_mm = pdfmetrics.stringWidth(item.text, font, item.size_pt) / mm
    if width_mm <= item.max_width:
        return item.size_pt
    return item.size_pt * item.max_width / width_mm


class PdfExporter:
    def export(self, pages: list[PageLayout], path: Path) -> None:
        register_pdf_fonts()
        if not pages:
            raise ValueError("그릴 대진이 없습니다.")
        canvas = Canvas(str(path), pagesize=(pages[0].width * mm, pages[0].height * mm))
        for page in pages:
            self._draw_page(canvas, page)
            canvas.showPage()
        canvas.save()

    def _draw_page(self, canvas: Canvas, page: PageLayout) -> None:
        height = page.height
        self._draw_shapes(canvas, page)
        canvas.setStrokeColorRGB(*LINE_COLOR)
        for line in page.lines:
            canvas.setLineWidth(line.width_pt)
            canvas.line(line.x1 * mm, (height - line.y1) * mm, line.x2 * mm, (height - line.y2) * mm)
        for item in page.texts:
            canvas.setFillColor(HexColor(item.color))
            font = _font_name(item)
            size = fitted_size(item, font)
            canvas.setFont(font, size)
            baseline = (height - item.y) * mm - size * BASELINE_SHIFT
            x = item.x * mm
            if item.align is Align.LEFT:
                canvas.drawString(x, baseline, item.text)
            elif item.align is Align.RIGHT:
                canvas.drawRightString(x, baseline, item.text)
            else:
                canvas.drawCentredString(x, baseline, item.text)

    @staticmethod
    def _draw_shapes(canvas: Canvas, page: PageLayout) -> None:
        height = page.height
        for rect in page.rects:
            canvas.setFillColor(HexColor(rect.fill))
            top = (height - rect.y - rect.height) * mm
            canvas.rect(rect.x * mm, top, rect.width * mm, rect.height * mm, stroke=0, fill=1)
        for polygon in page.polygons:
            canvas.setFillColor(HexColor(polygon.fill))
            path = canvas.beginPath()
            first, *rest = polygon.points
            path.moveTo(first[0] * mm, (height - first[1]) * mm)
            for x, y in rest:
                path.lineTo(x * mm, (height - y) * mm)
            path.close()
            canvas.drawPath(path, stroke=0, fill=1)
        for image in page.images:
            top = (height - image.y - image.height) * mm
            # mask="auto" 가 없으면 PNG 의 투명한 칸이 흰색으로 찍혀 마크 둘레에 흰 상자가 생긴다.
            reader = ImageReader(BytesIO(image.png))
            canvas.drawImage(reader, image.x * mm, top, image.width * mm, image.height * mm, mask="auto")
