from kendo_tournament.domain.photo_cover import cover_title_lines


def test_적어_둔_제목_줄이_있으면_그대로_쓴다():
    assert cover_title_lines("제5회\n광명 검도 축제\n", "아무 이름") == ["제5회", "광명 검도 축제"]


def test_비면_대회_이름을_회차_이름_검도대회_세_줄로_나눈다():
    assert cover_title_lines("", "제26회 광명시장기 검도대회") == ["제26회", "광명시장기", "검도대회"]
    assert cover_title_lines("", "제 19 회 광명시회장기검도대회") == ["제19회", "광명시회장기", "검도대회"]


def test_회차나_검도대회가_없으면_있는_만큼만_나눈다():
    assert cover_title_lines("", "광명 검도 축제") == ["광명 검도 축제"]
    assert cover_title_lines("", "제3회 검도대회") == ["제3회", "검도대회"]


def test_표지_맨_아래_주최_줄은_카탈로그처럼_이름표와_내용이_빈칸_하나로_붙는다():
    from kendo_tournament.domain.greeting import Photo
    from kendo_tournament.domain.layout.bracket_fit import printed_width_mm
    from kendo_tournament.domain.layout.photo_cover_page import (
        CREDIT_PT,
        LABEL_GAP,
        PhotoCoverContent,
        photo_front_cover,
    )

    value = "광명시, 광명시의회"
    content = PhotoCoverContent(("제1회",), "", "", (("후원", value),))
    page = photo_front_cover(content, Photo(b"", 0.7))
    shown, label = page.texts[-2], page.texts[-1]
    assert (shown.text, label.text) == (value, "후원")
    assert abs((shown.x - label.x) - (printed_width_mm(value, CREDIT_PT) + LABEL_GAP)) < 1e-9
    assert printed_width_mm(",", CREDIT_PT) < printed_width_mm("가", CREDIT_PT) / 3
