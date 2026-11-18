import pytest

from kendo_tournament.domain.division.category_label import Category, fill_missing_gender, parse_category
from kendo_tournament.domain.model import Gender

M, F = Gender.MALE, Gender.FEMALE


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("남초등 1~2학년", Category(M, 1, 2)),
        ("남초등 5~6학년부", Category(M, 5, 6)),
        ("여초등 4~6학년", Category(F, 4, 6)),
        ("초등저학년1~3학년", Category(None, 1, 3)),
        ("초등고학년 4~6학년", Category(None, 4, 6)),
        ("여청소년 (중,고)", Category(F, 7, 12)),
        ("남청소년부(중,고)", Category(M, 7, 12)),
        ("중등부", Category(None, 7, 9)),
        ("고등부", Category(None, 10, 12)),
        ("남자청년부 20~35세", Category(M, 13, 13, 20, 35)),
        ("남자중년부 48세부터", Category(M, 13, 13, 48, None)),
        ("여자일반부", Category(F, 13, 13)),
    ],
)
def test_신청서_종별_글을_성별_학년_나이로_읽는다(label, expected):
    assert parse_category(label) == expected


def test_학교급이_없는_메모는_종별이_아니다():
    assert parse_category("26명 참가") is None


def test_성별이_없는_중등부는_같은_학년대_여자_종별이_있으면_남자다():
    rows = [parse_category(text) for text in ("여청소년 (중,고)", "중등부", "고등부", "초등저학년1~3학년")]
    filled = fill_missing_gender(rows)
    assert [c.gender for c in filled] == [F, M, M, None]


def test_학년_없이_저학년_고학년만_적은_초등_종별은_요강_범위다():
    from kendo_tournament.domain.division.category_label import parse_category

    assert (parse_category("초등 저학년부").grade_from, parse_category("초등 저학년부").grade_to) == (1, 3)
    assert (parse_category("초등 고학년부").grade_from, parse_category("초등 고학년부").grade_to) == (4, 6)


def test_나이_범위_뒤에_이상이_붙으면_끝이_열린다():
    from kendo_tournament.domain.division.category_label import parse_category

    category = parse_category("남자중년부 40~50세이상")
    assert (category.age_from, category.age_to) == (40, None)


def test_전국대회_인제_종별_글도_읽는다():
    from kendo_tournament.domain.division.category_label import parse_category
    from kendo_tournament.domain.model import Gender

    def read(label):
        c = parse_category(label)
        return (c.gender, c.grade_from, c.grade_to, c.age_from, c.age_to)

    assert read("1,2학년") == (None, 1, 2, None, None)
    assert read("초등1~2학년부") == (None, 1, 2, None, None)
    assert read("여중부") == (Gender.FEMALE, 7, 9, None, None)
    assert read("남중부") == (Gender.MALE, 7, 9, None, None)
    assert read("남고부") == (Gender.MALE, 10, 12, None, None)
    assert read("여자부") == (Gender.FEMALE, 10, 13, None, None)
    assert read("20대 청년부") == (None, 13, 13, 20, 29)
    assert read("50대이상 노년부") == (None, 13, 13, 50, None)
    assert read("노년부 50세 이상") == (None, 13, 13, 50, None)


def test_요강이_저학년부_고학년부라고_부르면_그_이름을_대진_제목에_쓴다():
    from kendo_tournament.domain.division.category_label import group_name

    assert group_name("초등학교 저학년부") == "초등 저학년부"
    assert group_name("여자 초등 고학년부") == "초등 고학년부"
    assert group_name("초등저학년1~3학년") == "초등 저학년부"
    assert group_name("저학년 1~2학년") == "", "범위가 저학년(1~3)과 다르면 이름을 붙이지 않는다"
    assert group_name("남초등 1~2학년") == ""
