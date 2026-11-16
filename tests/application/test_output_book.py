from datetime import date
from pathlib import Path

import pytest

from kendo_tournament.application.output_book import CoverSources, OutputBook
from kendo_tournament.application.tournament_session import TournamentSession
from kendo_tournament.domain.greeting import Photo
from kendo_tournament.domain.layout.primitives import Align, PageLayout, TextItem
from kendo_tournament.domain.model import DivisionRule, Event, Gender, Grade, Participant
from kendo_tournament.domain.photo_cover import EXAMPLE_PREFIX, BackCoverPhoto, CoverChoice, CoverLogo, PhotoCoverSettings
from kendo_tournament.domain.ports import ExportError, InsertError
from kendo_tournament.infrastructure.readers.registry import reader_for
from kendo_tournament.infrastructure.storage.json_repository import JsonTournamentRepository
from tests.png_fixture import tiny_png


class FakeLogo:
    def __init__(self, mark: CoverLogo | None = None) -> None:
        self.mark = mark if mark is not None else CoverLogo(tiny_png(), 0.9)

    def load(self) -> CoverLogo | None:
        return self.mark

    def replace(self, source: Path) -> None:
        self.mark = CoverLogo(source.read_bytes(), 1.0)


class FakeInserter:
    def pages(self, path: Path) -> list[PageLayout]:
        return [PageLayout(texts=[TextItem(10, 10, f"끼운 문서 {path.name}", 10, Align.LEFT)])]


class FakeCoverDesign:
    def page(self, path: Path) -> PageLayout:
        if path.suffix not in (".pdf", ".png"):
            raise InsertError(f"{path.name}: 표지로 넣을 수 있는 파일은 PDF 입니다.")
        return PageLayout(texts=[TextItem(10, 10, f"가져온 표지 {path.name}", 10, Align.LEFT)])


class FakePhotos:
    def read(self, path: Path) -> Photo:
        if path.suffix != ".png":
            raise ExportError(f"대회사 사진은 PNG·JPG 파일만 넣을 수 있습니다: {path.name}")
        return Photo(b"png", 0.8)

    def read_front_cover(self, path: Path) -> Photo:
        self.read(path)
        return Photo(f"앞:{path.name}".encode(), 0.707)

    def read_back_cover(self, path: Path) -> BackCoverPhoto:
        self.read(path)
        return BackCoverPhoto(Photo(f"뒤:{path.name}".encode(), 0.707), logo_corner_dark=path.stem != "밝은뒤")


class FakeLibrary:
    @property
    def catalog_front(self) -> Path:
        return Path("카탈로그앞.png")

    @property
    def catalog_back(self) -> Path:
        return Path("카탈로그뒤.png")

    def tourism_badges(self) -> CoverLogo:
        return CoverLogo(b"badges", 1.9)

    def folder_photos(self, folder: Path) -> tuple[CoverChoice, ...]:
        return (CoverChoice("내 사진", str(folder / "내사진.png"), folder / "내사진.png"),)


def cover_sources(logo: FakeLogo | None = None, library: FakeLibrary | None = None) -> CoverSources:
    logo = logo if logo is not None else FakeLogo()
    return CoverSources(FakeCoverDesign(), FakePhotos(), logo, library if library is not None else FakeLibrary())


def ready_session(tmp_path):
    s = TournamentSession(JsonTournamentRepository(), reader_for, tmp_path)
    s.new("광명시장배")
    s.update_settings(held_on=date(2026, 11, 21))
    people = [Participant(str(i), f"선수{i}", Gender.MALE, f"도장{i % 3}", grade=Grade(1)) for i in range(4)]
    s.set_participants(people)
    s.set_rules([DivisionRule("r", Event.INDIVIDUAL, Gender.MALE, Grade(1), Grade(1))])
    s.draw_missing()
    return s


def texts(page):
    return [t.text for t in page.texts]


def test_앞표지_대회사_끼운_문서_대진표_뒤표지_순서로_묶는다(tmp_path):
    book = OutputBook(ready_session(tmp_path), FakeInserter(), cover_sources())
    book.add_inserts([Path("안내.pdf"), Path("일정.docx")])
    book.set_photo_cover(PhotoCoverSettings(photo="앞.png", back_photo="뒤.png"))
    pages = book.pages()
    assert "광명시장배" in texts(pages[0]) and "2026.11.21" in texts(pages[0])
    assert texts(pages[1])[0] == "대회사"
    assert texts(pages[2]) == ["끼운 문서 안내.pdf"] and texts(pages[3]) == ["끼운 문서 일정.docx"]
    assert texts(pages[4])[0] == "대회식순" and texts(pages[5])[0] == "일정안내"
    assert "남자 초1 개인전" in texts(pages[6])
    assert pages[-1].images[0].png == "뒤:뒤.png".encode()


def test_끼울_문서_순서를_바꾸고_뺄_수_있다(tmp_path):
    book = OutputBook(ready_session(tmp_path), FakeInserter(), cover_sources())
    book.add_inserts([Path("가.pdf"), Path("나.pdf"), Path("다.pdf")])
    book.move_insert(2, -1)
    assert [Path(p).name for p in book.settings.inserts] == ["가.pdf", "다.pdf", "나.pdf"]
    book.remove_insert(0)
    assert [Path(p).name for p in book.settings.inserts] == ["다.pdf", "나.pdf"]


def test_확인에서_모두_뺐으면_찍을_것이_없다고_알린다(tmp_path):
    session = ready_session(tmp_path)
    session.excluded_labels = set(session.print_order())
    with pytest.raises(ValueError, match="찍을 대진이 없습니다"):
        OutputBook(session, FakeInserter(), cover_sources()).pages()


def test_가져온_표지를_넣으면_글자를_얹지_않고_그대로_쓰고_빼면_사진_표지로_돌아온다(tmp_path):
    session = ready_session(tmp_path)
    book = OutputBook(session, FakeInserter(), cover_sources())
    designed = repr(book.pages()[0])
    book.use_cover_file(tmp_path / "만들어온표지.pdf")
    assert texts(book.pages()[0]) == ["가져온 표지 만들어온표지.pdf"]
    assert book.pages()[0].images == []
    reopened = TournamentSession(JsonTournamentRepository(), reader_for, tmp_path)
    reopened.open(session.path)
    assert Path(reopened.tournament.book.cover_file).name == "만들어온표지.pdf"
    book.stop_cover_file()
    assert repr(book.pages()[0]) == designed


def test_못_읽는_표지_파일은_거절하고_설정을_바꾸지_않는다(tmp_path):
    book = OutputBook(ready_session(tmp_path), FakeInserter(), cover_sources())
    with pytest.raises(InsertError):
        book.use_cover_file(tmp_path / "표지.txt")
    assert book.settings.cover_file == ""


def test_쪽_번호는_대회식순부터_1_이고_대진표로_이어진다(tmp_path):
    book = OutputBook(ready_session(tmp_path), FakeInserter(), cover_sources())
    book.add_inserts([Path("안내.pdf")])
    pages = book.pages()
    numbered = pages[3:-1]
    assert [page.texts[-1].text for page in numbered] == [str(n) for n in range(1, len(numbered) + 1)]


def test_식순_내용을_고치면_책자에_나오고_대회_파일에_남는다(tmp_path):
    from dataclasses import replace

    from kendo_tournament.domain.program import DEFAULT_PROGRAM

    session = ready_session(tmp_path)
    book = OutputBook(session, FakeInserter(), cover_sources())
    book.set_program(replace(DEFAULT_PROGRAM, officials=(("대회장", "김가람"),)))
    assert "김가람" in texts(book.pages()[2])
    assert session.tournament.book.program.officials == (("대회장", "김가람"),)


def test_뒤표지_파일을_넣으면_로고를_얹지_않고_그대로_쓴다(tmp_path):
    book = OutputBook(ready_session(tmp_path), FakeInserter(), cover_sources())
    book.set_photo_cover(PhotoCoverSettings(back_photo="뒤.png"))
    book.use_back_cover_file(Path("뒤표지.pdf"))
    back = book.pages()[-1]
    assert texts(back) == ["가져온 표지 뒤표지.pdf"] and back.images == []
    assert book.settings.back_cover_file == "뒤표지.pdf"
    book.stop_back_cover_file()
    assert book.settings.back_cover_file == ""


def test_대회사_날짜를_비우면_대회_날짜를_쓰고_내용을_고치면_대회_파일에_남는다(tmp_path):
    from dataclasses import replace

    session = ready_session(tmp_path)
    book = OutputBook(session, FakeInserter(), cover_sources())
    assert "2026. 11. 21" in texts(book.pages()[1])
    book.set_greeting(replace(book.settings.greeting, name="김가람", date_text="2026. 11. 1", photo_file="사진.png"))
    page = book.pages()[1]
    assert "김 가 람" in texts(page) and "2026. 11. 1" in texts(page) and page.images
    assert session.tournament.book.greeting.name == "김가람"


def test_못_읽는_대회사_사진은_저장하지_않는다(tmp_path):
    from dataclasses import replace

    import pytest

    book = OutputBook(ready_session(tmp_path), FakeInserter(), cover_sources())
    with pytest.raises(ExportError):
        book.set_greeting(replace(book.settings.greeting, photo_file="사진.bmp"))
    assert book.settings.greeting.photo_file == ""


def test_광명_대회는_사진을_안_고르면_카탈로그_앞표지_사진에_글을_얹고_뒤표지는_카탈로그_그대로다(tmp_path):
    book = OutputBook(ready_session(tmp_path), FakeInserter(), cover_sources())
    pages = book.pages()
    assert [image.png for image in pages[0].images] == ["앞:카탈로그앞.png".encode()]
    assert "광명시장배" in texts(pages[0])
    assert texts(pages[-1]) == ["가져온 표지 카탈로그뒤.png"], "그늘·로고 없이 완성 표지로 넣는다"


def test_표지_제목은_카탈로그_제목_글꼴로_찍는다(tmp_path):
    from kendo_tournament.domain.layout.photo_cover_page import TITLE_LEFT
    from kendo_tournament.domain.layout.primitives import Face

    session = ready_session(tmp_path)
    session.tournament.name = "제19회 광명시회장기 검도대회"
    book = OutputBook(session, FakeInserter(), cover_sources())
    book.set_photo_cover(PhotoCoverSettings(photo="앞.png"))
    front = book.pages()[0]
    title = [t for t in front.texts if t.x == TITLE_LEFT]
    assert title and all(t.face is Face.TITLE for t in title)
    assert all(t.face is Face.BODY for t in front.texts if t.x != TITLE_LEFT)


def test_표지_사진을_고르면_사진_표지에_정해진_자리로_글이_들어간다(tmp_path):
    from kendo_tournament.domain.layout.photo_cover_page import RIGHT_EDGE, TITLE_LEFT

    session = ready_session(tmp_path)
    session.tournament.name = "제19회 광명시회장기 검도대회"
    book = OutputBook(session, FakeInserter(), cover_sources())
    book.set_photo_cover(PhotoCoverSettings(photo="표지.png", venue="광명고등학교 검도체육관", sponsor=""))
    front = book.pages()[0]
    assert [image.png for image in front.images] == ["앞:표지.png".encode()] and front.images[0].width == 210.0
    title = [t for t in front.texts if t.x == TITLE_LEFT]
    assert [t.text for t in title] == ["제19회", "광명시회장기", "검도대회"]
    right = [t.text for t in front.texts if t.x == RIGHT_EDGE]
    assert "2026.11.21" in right and "광명고등학교 검도체육관" in right
    assert "후원" not in texts(front) and "주최" in texts(front)
    assert session.tournament.book.photo_cover.venue == "광명고등학교 검도체육관"


def test_뒤표지_사진을_고르면_카탈로그처럼_아래에_광명시_로고와_관광_로고_묶음이_들어간다(tmp_path):
    logo = FakeLogo(CoverLogo(b"dark-ink", 2.2, on_dark=b"white"))
    book = OutputBook(ready_session(tmp_path), FakeInserter(), cover_sources(logo))
    book.set_photo_cover(PhotoCoverSettings(back_photo="뒤.png"))
    background, placed, badges = book.pages()[-1].images
    assert background.png == "뒤:뒤.png".encode() and background.width == 210.0
    assert placed.x < 30 and placed.y + placed.height > 270
    assert placed.png == b"white", "어두운 자리에는 밝은 로고"
    assert badges.png == b"badges" and badges.x > 120 and badges.y + badges.height > 280
    assert abs(badges.width / badges.height - 1.9) < 1e-9


def test_뒤표지_로고_자리가_밝으면_진한_로고를_얹는다(tmp_path):
    logo = FakeLogo(CoverLogo(b"dark-ink", 2.2, on_dark=b"white"))
    book = OutputBook(ready_session(tmp_path), FakeInserter(), cover_sources(logo))
    book.set_photo_cover(PhotoCoverSettings(back_photo="밝은뒤.png"))
    assert book.pages()[-1].images[1].png == b"dark-ink"


def test_고르는_칸에는_카탈로그와_사진_폴더의_사진이_나온다(tmp_path):
    book = OutputBook(ready_session(tmp_path), FakeInserter(), cover_sources())
    assert book.cover_choice(front=True).ref == "" and book.cover_choice(front=True).label == "카탈로그"
    assert book.cover_choice(front=False).path == Path("카탈로그뒤.png")
    assert [c.label for c in book.folder_choices()] == ["내 사진"]


def test_예전_판에서_고른_배포본_예시_사진은_카탈로그로_읽는다(tmp_path):
    """예시 사진은 배포본에서 뺐다. 예전 대회 파일이 오류 없이 열리고 카탈로그 표지가 나와야 한다."""
    book = OutputBook(ready_session(tmp_path), FakeInserter(), cover_sources())
    book.set_photo_cover(PhotoCoverSettings(photo=EXAMPLE_PREFIX + "front_jodan.jpg", back_photo=EXAMPLE_PREFIX + "x.jpg"))
    pages = book.pages()
    assert pages[0].images[0].png == "앞:카탈로그앞.png".encode()
    assert texts(pages[-1]) == ["가져온 표지 카탈로그뒤.png"]


def national(tmp_path):
    from kendo_tournament.domain.tournament import Scope

    session = ready_session(tmp_path)
    session.update_settings(scope=Scope.NATIONAL)
    return session, OutputBook(session, FakeInserter(), cover_sources())


def test_전국_대회는_표지와_대회사_없이_식순부터_찍는다(tmp_path):
    _, book = national(tmp_path)
    pages = book.pages()
    assert texts(pages[0])[0] == "대회식순"
    assert "남자 초1 개인전" in texts(pages[-1]) or pages[-1].lines, "마지막은 대진표"
    assert all("가져온 표지" not in " ".join(texts(page)) for page in pages)


def test_전국_대회도_표지_파일을_넣으면_그것만_넣는다(tmp_path):
    _, book = national(tmp_path)
    book.use_cover_file(Path("앞.pdf"))
    book.use_back_cover_file(Path("뒤.pdf"))
    pages = book.pages()
    assert texts(pages[0]) == ["가져온 표지 앞.pdf"] and texts(pages[-1]) == ["가져온 표지 뒤.pdf"]


def test_전국_대회의_대회사는_틀로_넣거나_파일로_넣고_다시_뺄_수_있다(tmp_path):
    from kendo_tournament.domain.book import GreetingSource

    session, book = national(tmp_path)
    assert book.greeting_source() is GreetingSource.NONE
    book.set_greeting_source(GreetingSource.TEMPLATE)
    assert texts(book.pages()[0])[0] == "대회사"
    book.use_greeting_file(Path("회장인사.pdf"))
    assert texts(book.pages()[0]) == ["끼운 문서 회장인사.pdf"]
    assert session.tournament.book.greeting_file == "회장인사.pdf"
    book.set_greeting_source(GreetingSource.NONE)
    assert texts(book.pages()[0])[0] == "대회식순"


def test_광명_대회는_대회사를_늘_프로그램_틀로_넣는다(tmp_path):
    from kendo_tournament.domain.book import GreetingSource

    book = OutputBook(ready_session(tmp_path), FakeInserter(), cover_sources())
    book.set_greeting_source(GreetingSource.NONE)
    assert book.greeting_source() is GreetingSource.TEMPLATE
    assert texts(book.pages()[1])[0] == "대회사"


def test_못_읽는_표지_사진은_저장하지_않는다(tmp_path):
    book = OutputBook(ready_session(tmp_path), FakeInserter(), cover_sources())
    with pytest.raises(ExportError):
        book.set_photo_cover(PhotoCoverSettings(photo="표지.bmp"))
    assert book.settings.photo_cover.photo == ""
    with pytest.raises(ExportError):
        book.set_photo_cover(PhotoCoverSettings(back_photo="뒤.bmp"))
    assert book.settings.photo_cover.back_photo == ""
