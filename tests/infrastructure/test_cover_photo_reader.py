import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QColor, QImage  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from kendo_tournament.infrastructure.assets.photo_reader import PhotoFiles  # noqa: E402

APP = QApplication.instance() or QApplication([])


def _solid(path, color: str, width: int = 210, height: int = 297) -> None:
    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(QColor(color))
    image.save(str(path))


def _lightness(png: bytes, x_share: float, y_share: float) -> float:
    image = QImage.fromData(png)
    return image.pixelColor(int(image.width() * x_share), int(image.height() * y_share)).lightnessF()


def test_밝은_앞표지_사진은_글자_자리를_어둡게_눌러_흰_글자가_보이게_한다(tmp_path):
    path = tmp_path / "밝은.png"
    _solid(path, "#f4f4f4")
    photo = PhotoFiles().read_front_cover(path)
    assert _lightness(photo.png, 0.2, 0.02) < 0.6, "제목 자리"
    assert _lightness(photo.png, 0.8, 0.98) < 0.6, "날짜·주최 자리"
    assert _lightness(photo.png, 0.5, 0.6) > 0.9, "가운데는 그대로"


def test_어두운_앞표지_사진은_손대지_않는다(tmp_path):
    path = tmp_path / "어두운.png"
    _solid(path, "#141821")
    photo = PhotoFiles().read_front_cover(path)
    original = QColor("#141821").lightnessF()
    assert abs(_lightness(photo.png, 0.2, 0.02) - original) < 0.03


def test_뒤표지는_로고_자리가_어두운지_알려_준다(tmp_path):
    dark, light_left = tmp_path / "어두운.png", tmp_path / "왼쪽만밝은.png"
    _solid(dark, "#101010")
    image = QImage(210, 297, QImage.Format.Format_RGB32)
    image.fill(QColor("#101010"))
    for x in range(0, 80):
        for y in range(200, 297):
            image.setPixelColor(x, y, QColor("#f0f0f0"))
    image.save(str(light_left))
    assert PhotoFiles().read_back_cover(dark).logo_corner_dark
    assert not PhotoFiles().read_back_cover(light_left).logo_corner_dark, "오른쪽이 어두워 그늘을 안 깔면 왼쪽은 밝은 채다"


def test_표지_사진은_A4_비율로_잘라_온다(tmp_path):
    path = tmp_path / "가로.png"
    _solid(path, "#202020", width=600, height=300)
    photo = PhotoFiles().read_front_cover(path)
    assert abs(photo.aspect - 210 / 297) < 0.01


def test_뒤표지_사진의_아래가_밝으면_로고들이_보이게_아래만_눌러_둔다(tmp_path):
    path = tmp_path / "밝은뒤.png"
    _solid(path, "#f2f2f2")
    back = PhotoFiles().read_back_cover(path)
    assert _lightness(back.photo.png, 0.8, 0.95) < 0.6
    assert _lightness(back.photo.png, 0.5, 0.2) > 0.9, "위쪽은 그대로"
