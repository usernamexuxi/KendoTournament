from dataclasses import replace

from kendo_tournament.domain.draw.draw import draw_bracket
from kendo_tournament.domain.draw.numbering import number_matches
from kendo_tournament.domain.layout.booklet import CONTENT_BOTTOM, CONTENT_TOP, BookletItem, layout_booklet, page_numbers
from kendo_tournament.domain.layout.bracket_style import FINAL_LABEL, WHITE
from kendo_tournament.domain.layout.primitives import PAGE_HEIGHT, PAGE_WIDTH
from kendo_tournament.domain.model import Entry


def item(title, count, section="초등부 남자", new_page=False):
    entries = [Entry(f"{title}{i}", f"선수{i}", f"도장{i % 5}") for i in range(count)]
    bracket = draw_bracket(entries, title, 1)
    return BookletItem(section, bracket, number_matches(bracket), new_page)


def texts(page):
    return [t.text for t in page.texts]


def tabs(page):
    """쪽에 실린 부문 이름 띠의 글자(흰 굵은 글자, 「결승전」 제외)를 위에서 아래 순서로."""
    found = [t for t in page.texts if t.color == WHITE and t.bold and t.text != FINAL_LABEL]
    return [t.text for t in sorted(found, key=lambda t: t.y)]


def inside(page):
    points = [(t.x, t.y) for t in page.texts] + [(ln.x1, ln.y1) for ln in page.lines] + [(ln.x2, ln.y2) for ln in page.lines]
    return all(0 <= x <= PAGE_WIDTH and 0 <= y <= PAGE_HEIGHT for x, y in points)


def test_작은_대진_여럿은_한_쪽에_싣고_대진마다_부문_띠를_단다():
    pages = layout_booklet([item("남자 초1 개인전", 2), item("남자 초2 개인전", 4), item("남자 초3 개인전", 5)])
    assert len(pages) == 1
    assert tabs(pages[0]) == ["남자 초1 개인전", "남자 초2 개인전", "남자 초3 개인전"]
    assert inside(pages[0])


def test_참고_책자처럼_쪽_머리_묶음_제목은_없다():
    pages = layout_booklet([item("남자 초1 개인전", 3)])
    assert "초등부 남자" not in texts(pages[0])


def test_작은_묶음은_앞_쪽_빈자리에_이어_싣는다():
    pages = layout_booklet([item("남자 초1 개인전", 3), item("여자 초1 개인전", 3, section="초등부 여자")])
    assert len(pages) == 1
    assert tabs(pages[0]) == ["남자 초1 개인전", "여자 초1 개인전"]
    assert inside(pages[0])


def test_새_쪽으로_정한_묶음은_이어_싣지_않는다():
    second = item("여자 초1 개인전", 3, section="초등부 여자", new_page=True)
    pages = layout_booklet([item("남자 초1 개인전", 3), second])
    assert [tabs(p) for p in pages] == [["남자 초1 개인전"], ["여자 초1 개인전"]]


def test_자리가_모자라면_다음_묶음은_새_쪽이다():
    pages = layout_booklet([item("남자 초1 개인전", 30), item("여자 초1 개인전", 30, section="초등부 여자")])
    assert [tabs(p) for p in pages] == [["남자 초1 개인전"], ["여자 초1 개인전"]]


def test_부문_띠는_쪽_가운데에_있다():
    pages = layout_booklet([item("남자 초1 개인전", 3), item("남자 초2 개인전", 6)])
    centers = {t.x for t in pages[0].texts if t.text in ("남자 초1 개인전", "남자 초2 개인전")}
    assert centers == {PAGE_WIDTH / 2}


def test_결승은_번호_대신_결승전으로_표시한다():
    one = item("가", 4)
    pages = layout_booklet([one])
    assert FINAL_LABEL in texts(pages[0])
    assert str(one.numbered.root.number) not in texts(pages[0])


def test_새_쪽으로_넘기라고_한_부문은_새_쪽에서_시작한다():
    pages = layout_booklet([item("남자 초1 개인전", 3), item("남자 초2 개인전", 3, new_page=True)])
    assert len(pages) == 2


def test_자리가_모자라면_다음_쪽으로_넘긴다():
    pages = layout_booklet([item(f"남자 초{g} 개인전", 16) for g in range(1, 7)])
    assert len(pages) > 1
    assert all(inside(p) for p in pages)


def test_대진들이_서로_겹치지_않고_내용_구간_안에_있다():
    pages = layout_booklet([item("가", 3), item("나", 6), item("다", 2)])
    page = pages[0]
    assert tabs(page) == ["가", "나", "다"]
    body = [ln for ln in page.lines if ln.y1 > CONTENT_TOP]
    assert all(CONTENT_TOP <= ln.y1 <= CONTENT_BOTTOM for ln in body)


def test_한_쪽에_안_들어가는_큰_대진은_자기_쪽을_따로_쓴다():
    pages = layout_booklet([item("작은", 3), item("큰", 128), item("뒤", 3)])
    assert tabs(pages[0])[0] == "작은"
    assert len(pages) >= 4
    assert all(inside(p) for p in pages)


def test_쪽_번호는_바깥_모서리에_있다():
    pages = layout_booklet([item("가", 3), item("나", 3, new_page=True)])
    first, second = (p.texts[-1] for p in pages)
    assert (first.text, second.text) == ("1", "2")
    assert first.x > PAGE_WIDTH / 2 > second.x


def test_쪽_번호는_참고_책자와_같은_자리_크기다():
    pages = layout_booklet([item("가", 3), item("나", 3, new_page=True)])
    odd, even = (p.texts[-1] for p in pages)
    # 참고 책자(612×859pt) 실측: 바깥 끝에서 54pt, 글자 위끝 804pt, 10pt, 검정 80% → A4 로 비례 환산.
    assert abs((PAGE_WIDTH - odd.x) - 18.5) < 0.5 and abs(even.x - 18.5) < 0.5
    assert abs(odd.y - 279.7) < 0.5 and odd.size_pt == 10.0 and odd.color == "#333333"


def test_대진표는_쪽_번호_위에서_끝난다():
    pages = layout_booklet([item("가", 16)])
    number = pages[0].texts[-1]
    others = [t for t in pages[0].texts[:-1]]
    assert max(t.y for t in others) < number.y - 4


def test_3위_결정전_안내는_쓰지_않는다():
    pages = layout_booklet([item("가", 8)])
    assert not any("3위" in text for text in texts(pages[0]))


def test_넘치는_묶음은_쪽마다_고르게_나눠_한_대진만_외롭게_남지_않는다():
    sizes = (6, 8, 4, 8, 7, 8)
    grades = [item(f"남자 초{g} 개인전", count) for g, count in enumerate(sizes, start=1)]
    pages = layout_booklet(grades)
    counts = [len(tabs(p)) for p in pages]
    assert len(pages) == 2, counts
    assert max(counts) - min(counts) <= 1, counts
    assert inside(pages[0]) and inside(pages[1])


def test_고르게_나눠도_순서는_그대로다():
    pages = layout_booklet([item(f"남자 초{g} 개인전", 8) for g in range(1, 7)])
    order = [title for page in pages for title in tabs(page)]
    assert order == [f"남자 초{g} 개인전" for g in range(1, 7)]


def test_한_쪽에_다_들어가면_나누지_않는다():
    pages = layout_booklet([item(f"남자 초{g} 개인전", 4) for g in range(1, 4)])
    assert len(pages) == 1


def test_쪽_번호는_각_부문이_실린_쪽을_알려_준다():
    grades = [item(f"남자 초{g} 개인전", 8) for g in range(1, 7)]
    numbers = page_numbers(grades)
    pages = layout_booklet(grades)
    for grade, number in zip(grades, numbers, strict=True):
        assert grade.bracket.title in tabs(pages[number - 1])


def test_운영자가_정한_새_쪽은_고르게_나눌_때도_지킨다():
    grades = [item(f"남자 초{g} 개인전", 4, new_page=(g == 5)) for g in range(1, 7)]
    pages = layout_booklet(grades)
    assert [tabs(p) for p in pages] == [
        [f"남자 초{g} 개인전" for g in range(1, 5)],
        ["남자 초5 개인전", "남자 초6 개인전"],
    ]


def test_책자에서도_대진이_많아져도_이름_글자_크기는_그대로다():
    from kendo_tournament.domain.layout.bracket_layout import BRACKET_FONT_PT

    for counts in ([2, 4, 5], [16, 16, 16, 16], [3, 30, 3], [40]):
        pages = layout_booklet([item(f"부문{i}", n) for i, n in enumerate(counts)])
        for page in pages:
            assert inside(page)
            names = [t for t in page.texts if t.slot is not None]
            assert all(t.size_pt == BRACKET_FONT_PT for t in names)


def real(title, count, section="중등부 남자"):
    entries = [Entry(f"{title}{i}", "홍길동", "하안검도관") for i in range(count)]
    bracket = draw_bracket(entries, title, 1)
    return BookletItem(section, bracket, number_matches(bracket))


def test_들어가는_대진은_나누지_않는다():
    small = layout_booklet([real("남자 중2 개인전", 5), real("남자 중3 개인전", 10)])
    assert [tabs(page) for page in small] == [["남자 중2 개인전", "남자 중3 개인전"]]


def test_도저히_안_들어가는_대진만_나누고_조각마다_양쪽_대진이다():
    items = [real("남자 중2 개인전", 5), real("남자 일반부 개인전", 100)]
    pages = layout_booklet(items)
    assert sum(tabs(page).count("남자 일반부 개인전") for page in pages) > 1
    for page in pages:
        names = [t for t in page.texts if t.slot is not None]
        assert any(t.x < PAGE_WIDTH / 2 for t in names) and any(t.x > PAGE_WIDTH / 2 for t in names)
    assert all(n is not None for n in page_numbers(items))


def test_나눈_대진은_마지막_조각_아래에_남은_경기를_한_줄씩_적는다():
    entries = [Entry(str(i), "홍길동", "하안검도관") for i in range(100)]
    bracket = draw_bracket(entries, "남자 일반부 개인전", 1)
    numbered = number_matches(bracket)
    pages = layout_booklet([BookletItem("일반부 남자", bracket, numbered)])
    lines = [t.text for page in pages for t in page.texts if "번 경기:" in t.text]
    assert lines and lines[-1].startswith(f"결승 {numbered.root.number}번 경기:")
    assert all(inside(page) for page in pages)


def test_개인전과_단체전은_한_쪽에_이어_싣지_않는다():
    team = replace(item("남자 초1~초6 단체전", 3, section="초등부 남자 단체전"), is_team=True)
    pages = layout_booklet([item("여자 성인 개인전", 3, section="성인부 여자"), team])
    assert [tabs(p) for p in pages] == [["여자 성인 개인전"], ["남자 초1~초6 단체전"]]


def test_부문_띠와_맨_윗_이름_사이는_대진마다_같다():
    titles = ["가", "나", "다"]
    pages = layout_booklet([item(t, n) for t, n in zip(titles, (4, 7, 22), strict=True)])
    gaps = set()
    for page in pages:
        for tab in (t for t in page.texts if t.text in titles):
            below = [t.y for t in page.texts if t.slot is not None and t.y > tab.y]
            gaps.add(round(min(below) - tab.y, 3))
    assert len(gaps) == 1
