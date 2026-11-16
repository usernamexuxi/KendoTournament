"""대회사 사진·표지 사진을 읽는다. 허용 형식(PNG·JPG)만 받고, Qt 로 실제로 열어 그림인지 확인한다.

휴대폰 사진은 가로세로 수천 픽셀이라 그대로 넣으면 책자 PDF 가 수십 MB 가 된다. 쓰일 크기에 넉넉하게 줄인다.
표지 글자는 카탈로그처럼 흰색이라, 밝은 사진이면 글자 자리를 위·아래 그늘로 어둡게 눌러 글자가 보이게 한다.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter

from kendo_tournament.domain.greeting import Photo
from kendo_tournament.domain.photo_cover import BackCoverPhoto
from kendo_tournament.domain.ports import ExportError

ACCEPTED_PHOTO_SUFFIXES = (".png", ".jpg", ".jpeg")
PHOTO_FILTER = "사진 (*.png *.jpg *.jpeg)"
# 30mm 칸을 300dpi 로 찍으면 약 350픽셀이다. 확대해 보여도 깨지지 않게 두 배 남짓 둔다.
MAX_PIXELS = 800
# 표지는 쪽 전체에 깔려 대회사 사진보다 크게 찍힌다. A4 를 200dpi 남짓으로 덮는 크기.
COVER_PIXELS = 1800
PAGE_ASPECT = 210 / 297
JPEG_QUALITY = 88
# 밝기는 작게 줄인 그림에서 잰다(칸마다 재면 수백만 번이라 느리다).
SAMPLE_WIDTH, SAMPLE_HEIGHT = 42, 60
# 글자 자리(쪽 비율): 위 제목, 아래 날짜·장소·주최. 뒤표지 로고 자리는 왼쪽 아래.
TITLE_ZONE = (0.0, 0.0, 0.7, 0.33)
DETAIL_ZONE = (0.3, 0.84, 1.0, 1.0)
LOGO_ZONE = (0.0, 0.88, 0.32, 0.97)
BADGE_ZONE = (0.6, 0.82, 0.96, 0.97)
# 뒤표지 아래 로고들은 작고 가는 흰 글씨라, 평균이 아니라 밝은 쪽(상위 25%) 밝기로 재고 그늘도 더 진하고 넓게 깐다.
BRIGHT_SHARE = 0.25
BACK_CALM, BACK_RANGE, BACK_MAX_SHADE, BACK_SHADE_START = 0.3, 0.35, 0.72, 0.66
TOP_SHADE_END, BOTTOM_SHADE_START = 0.42, 0.76
# 이 밝기(0~1)까지는 흰 글자가 잘 보여 손대지 않는다. 그보다 밝을수록 그늘을 진하게(최대 MAX_SHADE).
CALM_LIGHTNESS, SHADE_RANGE, MAX_SHADE = 0.32, 0.4, 0.62
DARK_CORNER = 0.5
# 그늘은 가장자리 쪽 절반 남짓을 거의 그대로 유지하다가 안쪽에서 빠르게 옅어진다(글자 자리를 고르게 덮도록).
PLATEAU, PLATEAU_KEEP = 0.45, 0.85


class PhotoFiles:
    def read(self, path: Path) -> Photo:
        return _photo(_shrunk(_image(path), MAX_PIXELS))

    def read_front_cover(self, path: Path) -> Photo:
        image = _page_cut(_image(path))
        sample = _sample(image)
        top = _shade_strength(_lightness(sample, TITLE_ZONE))
        bottom = _shade_strength(_lightness(sample, DETAIL_ZONE))
        if top or bottom:
            image = _shaded(image, top, bottom)
        return _photo(_shrunk(image, COVER_PIXELS))

    def read_back_cover(self, path: Path) -> BackCoverPhoto:
        """아래쪽 로고들(흰 글씨가 많다)이 보이게, 아래가 밝으면 앞표지처럼 눌러 둔다. 로고 자리 밝기는 누른 뒤에 잰다."""
        image = _page_cut(_image(path))
        bright = _lightness(_sample(image), BADGE_ZONE, BRIGHT_SHARE)
        bottom = min(BACK_MAX_SHADE, max(0.0, (bright - BACK_CALM) / BACK_RANGE * BACK_MAX_SHADE))
        if bottom:
            image = _shaded(image, 0.0, bottom, BACK_SHADE_START)
        dark = _lightness(_sample(image), LOGO_ZONE) < DARK_CORNER
        return BackCoverPhoto(_photo(_shrunk(image, COVER_PIXELS)), dark)


def _page_cut(image: QImage) -> QImage:
    width, height = image.width(), image.height()
    if width / height > PAGE_ASPECT:
        cut = round(height * PAGE_ASPECT)
        return image.copy((width - cut) // 2, 0, cut, height)
    cut = round(width / PAGE_ASPECT)
    return image.copy(0, (height - cut) // 2, width, cut)


def _sample(image: QImage) -> QImage:
    ignore, smooth = Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation
    return image.scaled(SAMPLE_WIDTH, SAMPLE_HEIGHT, ignore, smooth)


def _lightness(sample: QImage, zone: tuple[float, float, float, float], brightest: float = 1.0) -> float:
    """자리의 평균 밝기. brightest 가 1 보다 작으면 가장 밝은 그만큼의 칸만 평균한다."""
    left, top, right, bottom = zone
    xs = range(int(left * sample.width()), max(int(left * sample.width()) + 1, int(right * sample.width())))
    ys = range(int(top * sample.height()), max(int(top * sample.height()) + 1, int(bottom * sample.height())))
    values = sorted((sample.pixelColor(x, y).lightnessF() for x in xs for y in ys), reverse=True)
    values = values[: max(1, round(len(values) * brightest))]
    return sum(values) / len(values)


def _shade_strength(lightness: float) -> float:
    return min(MAX_SHADE, max(0.0, (lightness - CALM_LIGHTNESS) / SHADE_RANGE * MAX_SHADE))


def _shaded(image: QImage, top: float, bottom: float, bottom_start: float = BOTTOM_SHADE_START) -> QImage:
    """위·아래에서 안쪽으로 옅어지는 검은 그늘을 덮는다. 가운데(사진의 주인공)는 그대로 둔다."""
    shaded = image.convertToFormat(QImage.Format.Format_RGB32)
    height, width = shaded.height(), shaded.width()
    painter = QPainter(shaded)
    for strength, start, end in ((top, 0.0, TOP_SHADE_END), (bottom, 1.0, bottom_start)):
        if not strength:
            continue
        gradient = QLinearGradient(QPointF(0, start * height), QPointF(0, end * height))
        gradient.setColorAt(0.0, QColor(0, 0, 0, round(strength * 255)))
        gradient.setColorAt(PLATEAU, QColor(0, 0, 0, round(strength * 255 * PLATEAU_KEEP)))
        gradient.setColorAt(1.0, QColor(0, 0, 0, 0))
        band = QRectF(0, min(start, end) * height, width, abs(end - start) * height)
        painter.fillRect(band, gradient)
    painter.end()
    return shaded


def _image(path: Path) -> QImage:
    if path.suffix.lower() not in ACCEPTED_PHOTO_SUFFIXES:
        raise ExportError(f"사진은 PNG·JPG 파일만 넣을 수 있습니다: {path.name}")
    image = QImage(str(path))
    if image.isNull():
        raise ExportError(f"사진을 열 수 없습니다. 파일이 옮겨졌으면 다시 골라 주세요: {path.name}")
    return image


def _shrunk(image: QImage, limit: int) -> QImage:
    if max(image.width(), image.height()) <= limit:
        return image
    keep, smooth = Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
    return image.scaled(limit, limit, keep, smooth)


def _photo(image: QImage) -> Photo:
    # 사진은 PNG 로 두면 표지 한 장이 수 MB 라 JPG 로 담는다. PDF(reportlab)·미리보기(Qt)는 형식을 알아서 읽는다.
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.convertToFormat(QImage.Format.Format_RGB32).save(buffer, "JPG", JPEG_QUALITY)
    return Photo(bytes(data), image.width() / image.height())
