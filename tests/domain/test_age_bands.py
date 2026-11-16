import pytest

from kendo_tournament.domain.division.age_bands import AgeBand, band_text, parse_age_bands, single_band
from kendo_tournament.domain.division.builder import build_divisions
from kendo_tournament.domain.model import DivisionRule, Event, Gender, Grade, Participant

FORM_BANDS = "청년부 20-35, 장년부 36-47, 중년부 48-"


def test_신청서_나이_구간_글을_청년_장년_중년으로_읽는다():
    assert parse_age_bands(FORM_BANDS) == [
        AgeBand("청년부", 20, 35),
        AgeBand("장년부", 36, 47),
        AgeBand("중년부", 48, None),
    ]


def test_빈_글이면_성인부를_나이로_나누지_않는다():
    assert parse_age_bands("") == []


def test_알아볼_수_없거나_겹치는_구간은_오류다():
    with pytest.raises(ValueError):
        parse_age_bands("청년부 이십-삼십")
    with pytest.raises(ValueError):
        parse_age_bands("청년부 20-40, 장년부 36-47")
    with pytest.raises(ValueError):
        parse_age_bands("중년부 48-, 노년부 60-")


def test_규칙_한_줄의_나이_칸은_구간_하나만_받고_글로_되돌릴_수_있다():
    band = single_band("장년부 36-47")
    assert band == AgeBand("장년부", 36, 47)
    assert band_text(band.name, band.start, band.end) == "장년부 36-47"
    with pytest.raises(ValueError):
        single_band(FORM_BANDS)


def test_종별_없는_선수는_나이에_맞는_구간_부문에_들어간다():
    adult = Grade(13)
    rules = [
        DivisionRule(f"r{i}", Event.INDIVIDUAL, Gender.MALE, adult, adult, None, None, band.start, band.end, band.name)
        for i, band in enumerate(parse_age_bands(FORM_BANDS))
    ]
    people = [Participant(str(age), f"선수{age}", Gender.MALE, "도장", age=age) for age in (20, 35, 36, 47, 48, 70)]
    result = build_divisions(people, [], rules)
    placed = {d.label: sorted(int(e.id) for e in d.entries) for d in result.divisions}
    assert placed == {
        "남자 청년부(20~35세) 개인전": [20, 35],
        "남자 장년부(36~47세) 개인전": [36, 47],
        "남자 중년부(48세부터) 개인전": [48, 70],
    }


def test_나이_칸에_부_이름만_적으면_나이_없이_이름만_남고_글로_되돌아온다():
    from kendo_tournament.domain.division.age_bands import rule_age

    assert rule_age("중년부") == (None, None, "중년부")
    assert rule_age("장년부 36-47") == (36, 47, "장년부")
    assert rule_age("") == (None, None, "")
    assert band_text("중년부", None, None) == "중년부"
