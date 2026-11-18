from kendo_tournament.domain.layout.bracket_boxes import (
    DOJANG_FILL,
    NUMBER_CELL,
    NUMBER_FILL,
    BoxPlace,
    boxes_width,
    dojang_column,
    draw_name_box,
)
from kendo_tournament.domain.layout.primitives import PageLayout
from kendo_tournament.domain.model import Entry

PLAYER = Entry("p1", "김소율", "산곡검도관")
TEAM = Entry("t1", "A", "산곡검도관", team=True)


def _drawn(entry: Entry, mirrored: bool, number: int | None = 7) -> tuple[PageLayout, BoxPlace]:
    page = PageLayout()
    width = boxes_width([entry], 15.5)
    place = BoxPlace(50.0, 100.0, width, 8.0, dojang_column([entry]), mirrored, slot=0)
    draw_name_box(page, entry, place, number)
    return page, place


def _text_x(page: PageLayout, text: str) -> float:
    return next(t.x for t in page.texts if t.text == text)


def test_왼쪽_대진은_도장_이름_번호_순서이고_번호가_선_쪽에_붙는다():
    page, place = _drawn(PLAYER, mirrored=False)
    dojang, name, number = _text_x(page, "산곡검도관"), _text_x(page, "김 소 율"), _text_x(page, "7")
    assert place.left < dojang < name < number < place.left + place.width
    assert number > place.left + place.width - NUMBER_CELL


def test_오른쪽_대진은_거울상이라_번호가_왼쪽_선_쪽에_붙는다():
    page, place = _drawn(PLAYER, mirrored=True)
    dojang, name, number = _text_x(page, "산곡검도관"), _text_x(page, "김 소 율"), _text_x(page, "7")
    assert place.left < number < name < dojang < place.left + place.width
    assert number < place.left + NUMBER_CELL


def test_도장_칸과_번호_칸은_색으로_구분된다():
    page, _ = _drawn(PLAYER, mirrored=False)
    assert {rect.fill for rect in page.rects} == {DOJANG_FILL, NUMBER_FILL}


def test_번호를_아직_안_매긴_화면에서는_번호_칸이_비어_있다():
    page, _ = _drawn(PLAYER, mirrored=False, number=None)
    assert not any(t.text.isdigit() for t in page.texts)


def test_단체전_상자는_도장_칸_없이_팀_이름과_번호만_있다():
    page, place = _drawn(TEAM, mirrored=False)
    assert {rect.fill for rect in page.rects} == {NUMBER_FILL}
    assert [t.text for t in page.texts] == ["산곡검도관A", "7"]
    inner = [ln.x1 for ln in page.lines if ln.x1 == ln.x2 and place.left < ln.x1 < place.left + place.width]
    assert len(inner) == 1


def test_도장_칸_폭은_대진에서_가장_긴_도장에_맞춘다():
    short, long = Entry("a", "가", "갑"), Entry("b", "나", "부평유소년검도단")
    assert dojang_column([short, long, None]) == dojang_column([long])
