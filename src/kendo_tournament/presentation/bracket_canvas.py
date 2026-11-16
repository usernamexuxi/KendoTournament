"""PageLayout 을 화면에 그대로 그린다. 인쇄물과 똑같이 보이도록 같은 좌표를 쓴다."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetricsF, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsPolygonItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
)

from kendo_tournament.domain.layout.bracket_layout import PAGE_HEIGHT, PAGE_WIDTH, Align, PageLayout, TextItem
from kendo_tournament.domain.layout.primitives import Face
from kendo_tournament.presentation.style import LINE, PRINT_FONT_FAMILY, PRINT_TITLE_FONT_FAMILY, SELECTED, WARN_SOFT

PX_PER_MM = 4.0
PT_TO_MM = 0.3528
PAGE_GAP_MM = 8.0
LINE_PEN_WIDTH = 0.9


class BracketCanvas(QGraphicsView):
    slot_clicked = Signal(int)

    def __init__(self, selectable: bool = True) -> None:
        """selectable 이 False 면 이름 칸을 누를 수 없다(출력 미리보기용)."""
        super().__init__()
        self._selectable = selectable
        self._page_tops: list[float] = []
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
        self.setBackgroundBrush(QColor("#e9edf1"))
        self._slot_boxes: dict[int, QGraphicsRectItem] = {}

    def show_pages(self, pages: list[PageLayout], highlighted: set[int], conflicts: set[int]) -> None:
        scene = self.scene()
        scene.clear()
        self._slot_boxes = {}
        self._page_tops = []
        top = 0.0
        for page in pages:
            self._page_tops.append(top)
            self._draw_page(page, top, highlighted, conflicts)
            top += (page.height + PAGE_GAP_MM) * PX_PER_MM
        # 종이 밖으로 나간 장식까지 넣어 재면 화면이 쓸데없이 넓어진다. 종이들만 감싼다.
        scene.setSceneRect(QRectF(0, 0, PAGE_WIDTH * PX_PER_MM, max(top, 1.0)).adjusted(-20, -20, 20, 20))

    def fit(self) -> None:
        self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    @property
    def page_count(self) -> int:
        return len(self._page_tops)

    def _page_rect(self, index: int) -> QRectF:
        top = self._page_tops[index]
        sheet = QRectF(0, top, PAGE_WIDTH * PX_PER_MM, PAGE_HEIGHT * PX_PER_MM)
        return sheet.adjusted(-10, -10, 10, 10)

    def fit_page(self, index: int) -> None:
        """한 쪽이 화면에 통째로 들어오게 맞춘다."""
        if 0 <= index < self.page_count:
            self.fitInView(self._page_rect(index), Qt.AspectRatioMode.KeepAspectRatio)

    def fit_width(self, index: int) -> None:
        """쪽 너비를 화면 너비에 맞추고 그 쪽 맨 위로 간다."""
        if not 0 <= index < self.page_count:
            return
        rect = self._page_rect(index)
        scale = self.viewport().width() / rect.width()
        self.resetTransform()
        self.scale(scale, scale)
        self.verticalScrollBar().setValue(round(rect.top() * scale))

    def visible_page(self) -> int:
        """화면 가운데에 걸린 쪽 번호(0부터)."""
        center = self.mapToScene(self.viewport().rect().center()).y()
        index = 0
        for i, top in enumerate(self._page_tops):
            if top <= center:
                index = i
        return index

    def _draw_page(self, page: PageLayout, top: float, highlighted: set[int], conflicts: set[int]) -> None:
        scene = self.scene()
        sheet = scene.addRect(
            0, top, page.width * PX_PER_MM, page.height * PX_PER_MM, QPen(QColor(LINE)), QBrush(Qt.GlobalColor.white)
        )
        sheet.setZValue(-1)
        self._draw_shapes(page, top, sheet)
        for line in page.lines:
            pen = QPen(QColor("#262626"), line.width_pt * LINE_PEN_WIDTH)
            scene.addLine(line.x1 * PX_PER_MM, top + line.y1 * PX_PER_MM, line.x2 * PX_PER_MM, top + line.y2 * PX_PER_MM, pen)
        for item in page.texts:
            self._draw_text(item, top, highlighted, conflicts)

    @staticmethod
    def _draw_shapes(page: PageLayout, top: float, sheet: QGraphicsRectItem) -> None:
        """면·다각형·그림은 종이에 딸린 자식으로 붙인다. 종이 밖으로 나간 부분은 인쇄처럼 잘려 보인다."""
        sheet.setFlag(QGraphicsItem.GraphicsItemFlag.ItemClipsChildrenToShape)
        no_pen = QPen(Qt.PenStyle.NoPen)
        for rect in page.rects:
            box = QRectF(rect.x * PX_PER_MM, top + rect.y * PX_PER_MM, rect.width * PX_PER_MM, rect.height * PX_PER_MM)
            item = QGraphicsRectItem(box, sheet)
            item.setPen(no_pen)
            item.setBrush(QBrush(QColor(rect.fill)))
        for polygon in page.polygons:
            points = QPolygonF([QPointF(x * PX_PER_MM, top + y * PX_PER_MM) for x, y in polygon.points])
            shape = QGraphicsPolygonItem(points, sheet)
            shape.setPen(no_pen)
            shape.setBrush(QBrush(QColor(polygon.fill)))
        for image in page.images:
            pixmap = QPixmap()
            pixmap.loadFromData(image.png)
            target = QSize(round(image.width * PX_PER_MM), round(image.height * PX_PER_MM))
            scaled = pixmap.scaled(target, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
            picture = QGraphicsPixmapItem(scaled, sheet)
            picture.setPos(image.x * PX_PER_MM, top + image.y * PX_PER_MM)

    def _draw_text(self, item: TextItem, top: float, highlighted: set[int], conflicts: set[int]) -> None:
        font = QFont(PRINT_TITLE_FONT_FAMILY if item.face is Face.TITLE else PRINT_FONT_FAMILY)
        font.setBold(item.bold)
        font.setPixelSize(max(1, round(item.size_pt * PT_TO_MM * PX_PER_MM)))
        metrics = QFontMetricsF(font)
        width = metrics.horizontalAdvance(item.text)
        if item.max_width and width > item.max_width * PX_PER_MM:
            font.setPixelSize(max(1, int(font.pixelSize() * item.max_width * PX_PER_MM / width)))
            metrics = QFontMetricsF(font)
            width = metrics.horizontalAdvance(item.text)
        x = item.x * PX_PER_MM
        if item.align is Align.RIGHT:
            x -= width
        elif item.align is Align.CENTER:
            x -= width / 2
        y = top + item.y * PX_PER_MM - metrics.height() / 2
        if item.slot is not None and self._selectable:
            self._slot_box(item.slot, QRectF(x - 3, y - 1, width + 6, metrics.height() + 2), highlighted, conflicts)
        text = QGraphicsSimpleTextItem(item.text)
        text.setBrush(QColor(item.color))
        text.setFont(font)
        text.setPos(x, y)
        self.scene().addItem(text)

    def _slot_box(self, slot: int, rect: QRectF, highlighted: set[int], conflicts: set[int]) -> None:
        color = SELECTED if slot in highlighted else WARN_SOFT if slot in conflicts else None
        box = self.scene().addRect(
            rect, QPen(Qt.PenStyle.NoPen), QBrush(QColor(color)) if color else QBrush(Qt.BrushStyle.NoBrush)
        )
        box.setData(0, slot)
        box.setCursor(Qt.CursorShape.PointingHandCursor)
        box.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self._slot_boxes[slot] = box

    def mousePressEvent(self, event) -> None:
        for item in self.items(event.position().toPoint()):
            slot = item.data(0)
            if isinstance(slot, int):
                self.slot_clicked.emit(slot)
                return
        super().mousePressEvent(event)

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self.scale(factor, factor)
            return
        super().wheelEvent(event)
