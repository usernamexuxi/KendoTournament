"""뒤표지에 얹을 광명시 로고. 운영자가 고른 그림을 저장 폴더에 PNG 로 보관하고, 없으면 배포본에 든 로고를 쓴다.

그림 형식은 허용 목록(PNG·JPG)만 받고, Qt 로 실제로 열어 그림인지 확인한 뒤 PNG 로 바꿔 둔다.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QImage

from kendo_tournament.domain.photo_cover import CoverLogo
from kendo_tournament.domain.ports import ExportError
from kendo_tournament.infrastructure.assets.cover_photos import CITY_LOGO
from kendo_tournament.infrastructure.assets.logo_cutout import cut_out

CITY_LOGO_NAME = "뒤표지로고.png"
ACCEPTED_LOGO_SUFFIXES = (".png", ".jpg", ".jpeg")


def _image(path: Path) -> QImage:
    if path.suffix.lower() not in ACCEPTED_LOGO_SUFFIXES:
        raise ExportError(f"로고 그림은 PNG·JPG 파일만 넣을 수 있습니다: {path.name}")
    image = QImage(str(path))
    if image.isNull():
        raise ExportError(f"그림 파일을 열 수 없습니다: {path.name}")
    return image


def _png_bytes(image: QImage) -> bytes:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(data)


def read_logo(path: Path) -> CoverLogo:
    """그림 파일을 로고로 읽는다. 흰 바탕은 지운다. 허용하지 않는 형식이거나 열 수 없으면 ExportError."""
    image = _image(path)
    on_light, on_dark = cut_out(_png_bytes(image))
    return CoverLogo(on_light, image.width() / image.height(), on_dark)


class CoverLogoFiles:
    """운영자가 고른 로고(저장 폴더의 CITY_LOGO_NAME) → 배포본 로고 순서로 찾는다. packaged 가 None 이면 배포본 로고가 없다."""

    def __init__(self, folder: Path, packaged: Path | None = CITY_LOGO, name: str = CITY_LOGO_NAME) -> None:
        self._user = folder / name
        self._packaged = packaged
        self._cached: tuple[Path, float, CoverLogo] | None = None

    def load(self) -> CoverLogo | None:
        """미리보기를 그릴 때마다 불린다. 흰 바탕 지우기가 느려 같은 파일(경로·수정 시각)이면 읽어 둔 것을 쓴다."""
        for path in (self._user, self._packaged):
            if path is not None and path.exists():
                return self._read(path)
        return None

    def _read(self, path: Path) -> CoverLogo:
        modified = path.stat().st_mtime
        if self._cached is not None and self._cached[:2] == (path, modified):
            return self._cached[2]
        mark = read_logo(path)
        self._cached = (path, modified, mark)
        return mark

    def replace(self, source: Path) -> None:
        image = _image(source)
        try:
            self._user.parent.mkdir(parents=True, exist_ok=True)
            self._user.write_bytes(_png_bytes(image))
        except OSError as error:
            raise ExportError(f"로고 그림을 저장할 수 없습니다: {self._user}") from error
