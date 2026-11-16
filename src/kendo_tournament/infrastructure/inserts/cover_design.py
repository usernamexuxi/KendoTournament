"""누가 따로 만들어 온 앞표지 파일을 A4 한 쪽으로 바꾼다.

PDF 는 첫 쪽만 쓴다 — 표지 파일에 뒷면까지 들어 있는 경우가 있어서다. 그림은 PNG·JPG 만 받는다.
가져온 표지는 이미 완성된 것이라 글·로고를 덧그리지 않고, 비율을 지켜 쪽 가운데에 앉힌다.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pypdfium2
from PIL import Image, UnidentifiedImageError

from kendo_tournament.domain.layout.primitives import PAGE_HEIGHT, PAGE_WIDTH, ImageItem, PageLayout
from kendo_tournament.domain.ports import InsertError
from kendo_tournament.infrastructure.inserts.document_inserter import pdf_pages

PDF_SUFFIX = ".pdf"
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg")
COVER_DESIGN_FILTER = "표지 디자인 (*.pdf *.png *.jpg *.jpeg)"


def _image_page(path: Path) -> PageLayout:
    with Image.open(path) as image:
        width_px, height_px = image.size
        buffer = BytesIO()
        image.save(buffer, format="PNG")
    scale = min(PAGE_WIDTH / width_px, PAGE_HEIGHT / height_px)
    width, height = width_px * scale, height_px * scale
    item = ImageItem((PAGE_WIDTH - width) / 2, (PAGE_HEIGHT - height) / 2, width, height, buffer.getvalue())
    return PageLayout(images=[item])


class CoverDesignFiles:
    def page(self, path: Path) -> PageLayout:
        suffix = path.suffix.lower()
        if suffix != PDF_SUFFIX and suffix not in IMAGE_SUFFIXES:
            raise InsertError(f"{path.name}: 표지로 넣을 수 있는 파일은 PDF · PNG · JPG 입니다.")
        if not path.exists():
            raise InsertError(f"{path.name}: 표지 파일을 찾을 수 없습니다. 옮겼거나 지웠는지 확인해 주세요.")
        try:
            pages = pdf_pages(path) if suffix == PDF_SUFFIX else [_image_page(path)]
        except (OSError, UnidentifiedImageError, pypdfium2.PdfiumError) as error:
            raise InsertError(f"{path.name}: 읽을 수 없는 표지 파일입니다 ({error}).") from error
        if not pages:
            raise InsertError(f"{path.name}: 표지 파일에 쪽이 없습니다.")
        return pages[0]
