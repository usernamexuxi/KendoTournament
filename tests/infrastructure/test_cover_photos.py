from kendo_tournament.infrastructure.assets.cover_photos import COVER_DIR, PackagedCoverPhotos


def test_배포본_표지_사진은_카탈로그_앞뒤표지뿐이다():
    """운영자 지시: 무료 예시 사진은 빼고, 광명 기본 표지(카탈로그)만 남긴다."""
    library = PackagedCoverPhotos()
    photos = {path.name for path in COVER_DIR.iterdir() if path.suffix.lower() in (".jpg", ".jpeg")}
    assert photos == {library.catalog_front.name, library.catalog_back.name}
    assert library.catalog_front.exists() and library.catalog_back.exists()


def test_사진_폴더의_사진만_고를_거리로_보여_주고_없으면_폴더를_만든다(tmp_path):
    folder = tmp_path / "표지사진"
    library = PackagedCoverPhotos()
    assert library.folder_photos(folder) == () and folder.is_dir()
    (folder / "우리 도장.jpg").write_bytes(b"x")
    (folder / "메모.txt").write_text("x", encoding="utf-8")
    assert [choice.label for choice in library.folder_photos(folder)] == ["우리 도장"]


def test_관광_로고_묶음은_가로로_긴_투명_바탕_그림이다():
    from io import BytesIO

    from PIL import Image

    badges = PackagedCoverPhotos().tourism_badges()
    assert badges.aspect > 1.5
    assert Image.open(BytesIO(badges.png)).mode == "RGBA"
