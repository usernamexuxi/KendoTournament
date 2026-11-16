"""표지 재료: 광명 대회 기본 표지인 참고 카탈로그(자체 제작) 앞·뒤표지 사진, 뒤표지 관광 로고 묶음, 운영자 사진 폴더.

무료 예시 사진은 운영자 지시로 뺐다. 출처는 assets/cover/출처.txt.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, UnidentifiedImageError

from kendo_tournament.domain.photo_cover import CoverChoice, CoverLogo
from kendo_tournament.domain.ports import ExportError

COVER_DIR = Path(__file__).resolve().parents[2] / "assets" / "cover"
CATALOG_FRONT = COVER_DIR / "catalog_front.jpg"
CATALOG_BACK = COVER_DIR / "catalog_back.jpg"
CITY_LOGO = COVER_DIR / "city_logo.png"
TOURISM_BADGES = COVER_DIR / "tour_badges.png"
PHOTO_SUFFIXES = (".png", ".jpg", ".jpeg")


class PackagedCoverPhotos:
    def __init__(self, folder: Path = COVER_DIR) -> None:
        self._folder = folder

    @property
    def catalog_front(self) -> Path:
        return self._folder / CATALOG_FRONT.name

    @property
    def catalog_back(self) -> Path:
        return self._folder / CATALOG_BACK.name

    def tourism_badges(self) -> CoverLogo:
        path = self._folder / TOURISM_BADGES.name
        try:
            with Image.open(path) as image:
                aspect = image.width / image.height
            return CoverLogo(path.read_bytes(), aspect)
        except (OSError, UnidentifiedImageError) as error:
            raise ExportError(f"뒤표지 로고 그림을 읽을 수 없습니다. 프로그램을 다시 설치해 주세요: {path.name}") from error

    def folder_photos(self, folder: Path) -> tuple[CoverChoice, ...]:
        try:
            folder.mkdir(parents=True, exist_ok=True)
            files = sorted(path for path in folder.iterdir() if path.suffix.lower() in PHOTO_SUFFIXES)
        except OSError as error:
            raise ExportError(f"「{folder.name}」 폴더를 열 수 없습니다: {error}") from error
        return tuple(CoverChoice(path.stem, str(path), path) for path in files)
