from pathlib import Path

import pytest

from kendo_tournament.domain.ports import ExportError
from kendo_tournament.infrastructure.assets.cover_logo import CITY_LOGO_NAME, CoverLogoFiles, read_logo
from kendo_tournament.infrastructure.assets.cover_photos import CITY_LOGO
from tests.png_fixture import tiny_png


def test_PNG_마크는_가로세로_비율과_함께_읽는다(tmp_path):
    path = tmp_path / "mark.png"
    path.write_bytes(tiny_png(8, 10))
    assert read_logo(path).aspect == pytest.approx(0.8)


def test_그림이_아니면_알려_준다(tmp_path):
    path = tmp_path / "mark.png"
    path.write_bytes(b"not an image")
    with pytest.raises(ExportError, match="열 수 없습니다"):
        read_logo(path)


def test_허용하지_않은_형식은_받지_않는다(tmp_path):
    path = tmp_path / "mark.gif"
    path.write_bytes(tiny_png())
    with pytest.raises(ExportError, match="PNG·JPG"):
        read_logo(path)


def test_마크를_고른_적이_없고_배포본에도_없으면_없음이다(tmp_path):
    assert CoverLogoFiles(tmp_path / "저장", packaged=tmp_path / "없음.png").load() is None


def test_배포본_마크가_있으면_그것을_쓴다(tmp_path):
    packaged = tmp_path / "cover_logo.png"
    packaged.write_bytes(tiny_png(10, 10))
    assert CoverLogoFiles(tmp_path / "저장", packaged=packaged).load().aspect == pytest.approx(1.0)


def test_고른_마크는_저장_폴더에_남고_배포본보다_먼저_쓴다(tmp_path):
    packaged = tmp_path / "cover_logo.png"
    packaged.write_bytes(tiny_png(10, 10))
    chosen = tmp_path / "고른마크.png"
    chosen.write_bytes(tiny_png(6, 12))
    store = CoverLogoFiles(tmp_path / "저장", packaged=packaged)
    store.replace(chosen)
    assert (tmp_path / "저장" / CITY_LOGO_NAME).exists()
    assert store.load().aspect == pytest.approx(0.5)


def test_배포본_광명시_로고는_밝은_바탕용과_어두운_바탕용_두_판이_있다():
    logo = CoverLogoFiles(Path("없는 저장 폴더")).load()
    assert logo is not None and logo.on_dark is not None and logo.on_dark != logo.png
    assert logo.aspect == pytest.approx(read_logo(CITY_LOGO).aspect)
