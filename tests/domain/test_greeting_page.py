from kendo_tournament.domain.greeting import Greeting, Photo
from kendo_tournament.domain.layout.greeting_page import NAME_Y, PHOTO_TOP, SIGN_RIGHT, TEXT_LEFT, TEXT_RIGHT, greeting_page
from kendo_tournament.domain.layout.primitives import PAGE_WIDTH, Align, estimated_width_mm

LONG = "가나다라마바사아자차카타파하 " * 12
GREETING = Greeting(body=f"첫 문단 {LONG}\n\n둘째 문단 {LONG}", position="광명시 검도회장", name="김가람")


def test_사진은_왼쪽_위에_첫_문단은_사진_오른쪽에_붙는다():
    page = greeting_page(GREETING, "2026. 11. 21", Photo(b"png", 0.8))
    photo = page.images[0]
    assert (photo.x, photo.y) == (TEXT_LEFT, PHOTO_TOP)
    first = next(t for t in page.texts if t.text.strip().startswith("첫 문단"))
    second = next(t for t in page.texts if t.text.strip().startswith("둘째 문단"))
    assert first.x > photo.x + photo.width
    assert second.x == TEXT_LEFT and second.y > photo.y + photo.height


def test_본문은_좌우_여백_안에서_줄을_바꾼다():
    page = greeting_page(GREETING, "", None)
    body = [t for t in page.texts if t.align is Align.LEFT and t.text != "대회사"]
    assert body and all(t.x + estimated_width_mm(t.text, t.size_pt) <= TEXT_RIGHT + 0.5 for t in body)


def test_날짜_직함_이름은_오른쪽_아래에_오른쪽_끝을_맞추고_이름은_글자를_띄운다():
    page = greeting_page(GREETING, "2026. 11. 21", None)
    signature = [t for t in page.texts if t.align is Align.RIGHT]
    assert [t.text for t in signature] == ["2026. 11. 21", "광명시 검도회장", "김 가 람"]
    assert all(t.x == SIGN_RIGHT and t.x > PAGE_WIDTH / 2 for t in signature)
    assert signature[-1].y == NAME_Y and signature[-1].size_pt > signature[0].size_pt


def test_사진이_없으면_글이_사진_자리부터_폭_가득_시작한다():
    page = greeting_page(GREETING, "", None)
    first = next(t for t in page.texts if t.text.strip().startswith("첫 문단"))
    assert not page.images and first.x == TEXT_LEFT
