from kendo_tournament.domain.draw.draw import draw_bracket
from kendo_tournament.domain.draw.numbering import number_matches
from kendo_tournament.domain.layout.bracket_layout import (
    BRACKET_FONT_PT,
    PAGE_HEIGHT,
    PAGE_WIDTH,
)
from kendo_tournament.domain.layout.bracket_pages import layout_bracket
from kendo_tournament.domain.layout.bracket_style import FINAL_LABEL, FINAL_WIDTH, TAB_PT, WHITE
from kendo_tournament.domain.model import Entry
from tests.domain.test_numbering_and_editing import example_b_group


def entries(n):
    return [Entry(str(i), f"선수{i}", f"도장{i % 7}") for i in range(n)]


def inside_page(page):
    points = (
        [(t.x, t.y) for t in page.texts]
        + [(line.x1, line.y1) for line in page.lines]
        + [(line.x2, line.y2) for line in page.lines]
    )
    return all(0 <= x <= PAGE_WIDTH and 0 <= y <= PAGE_HEIGHT for x, y in points)


def test_예시_B조는_도장_이름_경기번호만_있다():
    bracket = example_b_group()
    pages = layout_bracket(bracket, number_matches(bracket))
    texts = [t.text for page in pages for t in page.texts]
    assert any(text.startswith("남자 단부 개인전 B조") for text in texts)
    assert {"선 수 2 7", "도장27"} <= set(texts)
    numbers = sorted(int(t) for t in texts if t.isdigit())
    assert set(range(1, 25)) <= set(numbers)
    assert all(inside_page(page) for page in pages)


def test_인원이_늘어도_이름_글자와_제목_글자_크기는_그대로다():
    for count in (2, 4, 8, 16, 24, 32, 50, 128):
        bracket = draw_bracket(real_entries(count), "부문", 3)
        pages = layout_bracket(bracket, number_matches(bracket))
        for page in pages:
            assert inside_page(page), count
            tab = [t for t in page.texts if t.color == WHITE and t.text != FINAL_LABEL]
            assert tab and all(t.size_pt == TAB_PT for t in tab), count
            names = [t for t in page.texts if t.slot is not None]
            assert names and all(t.size_pt == BRACKET_FONT_PT for t in names), count


def real_entries(n):
    return [Entry(str(i), "홍길동", "하안검도관") for i in range(n)]


def test_한_쪽에_넣으면_글자가_너무_작아지는_큰_대진은_왼쪽_오른쪽_쪽으로_나눈다():
    bracket = draw_bracket(real_entries(50), "남자 중1~고3 개인전", 3)
    pages = layout_bracket(bracket, number_matches(bracket))
    assert len(pages) >= 2
    assert all(inside_page(page) for page in pages)


def test_한_쪽에_그린_양쪽_대진은_회전_사이가_넉넉해_번호가_이름에_겹치지_않는다():
    from kendo_tournament.domain.layout.bracket_boxes import BOX_LINE_PT
    from kendo_tournament.domain.layout.bracket_fit import MIN_ROUND_STEP
    from kendo_tournament.domain.layout.bracket_layout import fits_two_sided

    for count in (4, 6, 8):
        bracket = draw_bracket(real_entries(count), "부문", 3)
        assert fits_two_sided(bracket, number_matches(bracket).root), count
        pages = layout_bracket(bracket, number_matches(bracket))
        assert len(pages) == 1, count
        rounds = [line for line in pages[0].lines if line.x1 == line.x2 and line.width_pt != BOX_LINE_PT]
        verticals = sorted({round(line.x1, 3) for line in rounds})
        left = [x for x in verticals if x < PAGE_WIDTH / 2]
        assert all(b - a >= MIN_ROUND_STEP - 1e-6 for a, b in zip(left, left[1:], strict=False)), count


def test_단독_출전():
    bracket = draw_bracket(entries(1), "한명", 3)
    pages = layout_bracket(bracket, number_matches(bracket))
    assert "단독 출전" in pages[0].texts[1].text


def test_두명():
    bracket = draw_bracket(entries(2), "두명", 3)
    pages = layout_bracket(bracket, number_matches(bracket))
    assert len(pages) == 1 and inside_page(pages[0])


def test_부전승이_없는_작은_대진은_가로선이_쪽_끝까지_늘어나지_않는다():
    from kendo_tournament.domain.layout.bracket_boxes import BOX_LINE_PT
    from kendo_tournament.domain.layout.bracket_layout import FINAL_HALF_WIDTH, MAX_ROUND_STEP

    for count in (2, 4):
        bracket = draw_bracket(entries(count), "작은 부문", 1)
        page = layout_bracket(bracket, number_matches(bracket))[0]
        widths = [abs(ln.x2 - ln.x1) for ln in page.lines if ln.y1 == ln.y2 and ln.width_pt != BOX_LINE_PT]
        assert widths
        assert max(widths) <= max(MAX_ROUND_STEP, 2 * FINAL_HALF_WIDTH) + 1e-6


def both_sides(page):
    names = [t for t in page.texts if t.slot is not None]
    return any(t.x < PAGE_WIDTH / 2 for t in names) and any(t.x > PAGE_WIDTH / 2 for t in names)


def test_넘치는_대진은_부로_나누고_부마다_양쪽_대진이다():
    for count in (50, 128):
        bracket = draw_bracket(real_entries(count), "성인 남자", 3)
        pages = layout_bracket(bracket, number_matches(bracket))
        titles = [page.texts[0].text for page in pages]
        assert len(pages) > 1 and titles == [f"성인 남자 ({i})" for i in range(1, len(pages) + 1)], count
        assert all(both_sides(page) for page in pages), count
        names = [t.text for page in pages for t in page.texts if t.slot is not None]
        assert len(names) == count
        assert not any("경기로" in t.text for page in pages for t in page.texts), count


def test_들어가는_대진은_나누지_않는다():
    for count in (6, 10, 16):
        bracket = draw_bracket(real_entries(count), "남자 중3 개인전", 3)
        pages = layout_bracket(bracket, number_matches(bracket))
        assert [page.texts[0].text for page in pages] == ["남자 중3 개인전"], count
        assert both_sides(pages[0]), count


def test_32명까지는_나누지_않고_한_쪽에_양쪽_대진이다():
    bracket = draw_bracket(real_entries(32), "성인 남자", 3)
    pages = layout_bracket(bracket, number_matches(bracket))
    assert [page.texts[0].text for page in pages] == ["성인 남자"]
    assert both_sides(pages[0]) and inside_page(pages[0])


def test_결승전은_인원이_달라도_대진의_정가운데에_오고_양쪽은_같은_높이를_쓴다():
    """참고 책자(제26회 광명시장기 카탈로그): 적은 쪽은 고르게 퍼지고 「결승전」이 가로·세로 정가운데에 온다."""
    for count in (3, 5, 7, 13, 25):
        bracket = draw_bracket(real_entries(count), "부문", 3)
        page = layout_bracket(bracket, number_matches(bracket))[0]
        final = next(t for t in page.texts if t.text == FINAL_LABEL)
        names = [t for t in page.texts if t.slot is not None]
        left = [t.y for t in names if t.x < PAGE_WIDTH / 2]
        right = [t.y for t in names if t.x > PAGE_WIDTH / 2]
        assert abs(final.x - PAGE_WIDTH / 2) < 0.01, count
        assert abs((min(left) + max(left)) / 2 - (min(right) + max(right)) / 2) < 0.5, count
        top = min(left + right)
        bottom = max(left + right)
        assert abs(final.y - (top + bottom) / 2) < 0.5, count


def test_결승전_상자는_양쪽_준결승선의_한가운데에_온다():
    """양쪽 회전 수가 달라도(5명 = 2:3, 17명 = 8:9) 결승선 양 끝이 가운데에서 같은 거리여야 「결승전」이 가운데로 보인다.

    3명(1:2)은 한쪽이 경기 없이 이름에서 바로 결승선으로 이어져 세로선이 없으므로 뺀다.
    """
    for count in (5, 6, 9, 12, 13, 17, 25):
        bracket = draw_bracket(real_entries(count), "부문", 3)
        page = layout_bracket(bracket, number_matches(bracket))[0]
        final = next(t for t in page.texts if t.text == FINAL_LABEL)
        box_edges = (final.x - FINAL_WIDTH / 2, final.x + FINAL_WIDTH / 2)
        joins = [line for line in page.lines if line.y1 == line.y2 == final.y and {line.x1, line.x2} & set(box_edges)]
        left_end = min(min(line.x1, line.x2) for line in joins)
        right_end = max(max(line.x1, line.x2) for line in joins)
        assert abs((final.x - left_end) - (right_end - final.x)) < 0.01, count
