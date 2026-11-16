from kendo_tournament.domain.layout.document_pages import BOTTOM, DocParagraph, DocTable, document_pages, wrap


def test_긴_문단은_줄을_바꾸고_쪽이_넘치면_다음_쪽으로_간다():
    assert len(wrap("가" * 200, 50, 11)) > 1
    pages = document_pages([DocParagraph("대회 안내 " * 60) for _ in range(20)])
    assert len(pages) > 1
    assert all(t.y <= BOTTOM for page in pages for t in page.texts)


def test_표는_칸_글자와_테두리를_그린다():
    pages = document_pages([DocTable((("시간", "내용"), ("09:00", "개회식")))])
    texts = [t.text for t in pages[0].texts]
    assert {"시간", "내용", "09:00", "개회식"} <= set(texts)
    assert len(pages[0].lines) >= 6


def test_내용이_없으면_쪽도_없다():
    assert document_pages([]) == []
