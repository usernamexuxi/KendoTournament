import pytest

from kendo_tournament.domain.layout.document_pages import DocParagraph, document_pages
from kendo_tournament.domain.layout.primitives import PAGE_HEIGHT, PAGE_WIDTH
from kendo_tournament.domain.ports import InsertError
from kendo_tournament.infrastructure.exporters.pdf_exporter import PdfExporter
from kendo_tournament.infrastructure.inserts.cover_design import CoverDesignFiles
from tests.png_fixture import tiny_png


def test_그림_표지는_비율을_지켜_쪽_안_가운데에_앉는다(tmp_path):
    path = tmp_path / "표지.png"
    path.write_bytes(tiny_png(40, 10))
    image = CoverDesignFiles().page(path).images[0]
    assert image.width == pytest.approx(PAGE_WIDTH) and image.height == pytest.approx(PAGE_WIDTH / 4)
    assert image.y == pytest.approx((PAGE_HEIGHT - image.height) / 2)


def test_PDF_표지는_첫_쪽만_쓴다(tmp_path):
    path = tmp_path / "표지.pdf"
    PdfExporter().export(document_pages([DocParagraph("앞")]) * 2, path)
    page = CoverDesignFiles().page(path)
    assert len(page.images) == 1 and page.images[0].png.startswith(b"\x89PNG")


@pytest.mark.parametrize("name", ["표지.docx", "표지.hwp", "표지.gif"])
def test_허용하지_않는_형식은_거절한다(tmp_path, name):
    path = tmp_path / name
    path.write_bytes(b"x")
    with pytest.raises(InsertError, match="PDF · PNG · JPG"):
        CoverDesignFiles().page(path)


def test_없거나_깨진_표지_파일은_알아듣게_알린다(tmp_path):
    with pytest.raises(InsertError, match="찾을 수 없습니다"):
        CoverDesignFiles().page(tmp_path / "없음.png")
    broken = tmp_path / "깨짐.png"
    broken.write_bytes(b"not a png")
    with pytest.raises(InsertError, match="읽을 수 없는"):
        CoverDesignFiles().page(broken)


def _logo_like_png() -> bytes:
    """흰 바탕 위에 파랑 칸 · 흰 붓 획 · 주황 칸(엠블럼)과 검은 글자 한 칸."""
    from io import BytesIO

    from PIL import Image

    image = Image.new("RGB", (40, 10), (255, 255, 255))
    for y in range(2, 8):
        image.putpixel((3, y), (27, 69, 143))
        image.putpixel((7, y), (243, 99, 42))
        image.putpixel((20, y), (33, 34, 33))
        image.putpixel((24, y), (33, 34, 33))
    for x in range(20, 25):
        image.putpixel((x, 2), (33, 34, 33))
        image.putpixel((x, 7), (33, 34, 33))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_마크의_바깥_흰_바탕은_지우고_엠블럼_안_흰색은_남긴다():
    from io import BytesIO

    from PIL import Image

    from kendo_tournament.infrastructure.assets.logo_cutout import cut_out

    on_light, on_dark = cut_out(_logo_like_png())
    light, dark = Image.open(BytesIO(on_light)), Image.open(BytesIO(on_dark))
    assert light.getpixel((30, 1))[3] == 0 and light.getpixel((1, 5))[3] == 0
    assert dark.getpixel((22, 5))[3] == 0, "글자 「ㅁ」 속처럼 둘러싸인 흰 칸도 지운다"
    assert light.getpixel((5, 5)) == (255, 255, 255, 255)
    assert light.getpixel((20, 5))[:3] != (255, 255, 255) and dark.getpixel((20, 5)) == (255, 255, 255, 255)
    assert dark.getpixel((3, 5)) == (27, 69, 143, 255)


def test_배포본에_Pretendard_와_표지_제목_글꼴과_이용_조건이_들어_있다():
    from kendo_tournament.infrastructure.exporters.fonts import FONT_DIR, require_fonts

    regular, bold, title = require_fonts()
    assert regular.read_bytes()[:4] == bold.read_bytes()[:4] == title.read_bytes()[:4] == b"\x00\x01\x00\x00"
    assert "SIL Open Font License" in (FONT_DIR / "Pretendard-OFL.txt").read_text(encoding="utf-8")
    assert "상업적으로 이용이 가능" in (FONT_DIR / "ChungjuKimSaeng-license.txt").read_text(encoding="utf-8")
