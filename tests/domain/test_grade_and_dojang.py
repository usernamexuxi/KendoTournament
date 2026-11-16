import pytest

from kendo_tournament.domain.division.dojang import dojang_key
from kendo_tournament.domain.division.grade import grade_from_age, parse_grade, parse_school_grade, resolve_grade
from kendo_tournament.domain.model import Gender, Grade, Participant


@pytest.mark.parametrize(
    ("age", "label"),
    [(8, "초1"), (13, "초6"), (14, "중1"), (16, "중3"), (17, "고1"), (19, "고3"), (20, "성인"), (45, "성인")],
)
def test_연나이_경계값을_구분으로_바꾼다(age, label):
    assert grade_from_age(age).label == label


def test_8세_미만은_판단하지_않는다():
    assert grade_from_age(7) is None


@pytest.mark.parametrize(
    ("text", "label"),
    [
        ("초3", "초3"),
        ("초등 3", "초3"),
        ("초등학교 3학년", "초3"),
        ("중1", "중1"),
        ("고 2", "고2"),
        ("성인", "성인"),
        ("일반", "성인"),
    ],
)
def test_학년_표기를_읽는다(text, label):
    assert parse_grade(text).label == label


@pytest.mark.parametrize("text", ["3학년", "", "중4", "초7", "아무말"])
def test_학교급이_없거나_범위밖이면_None(text):
    assert parse_grade(text) is None


def test_적힌_학년이_나이보다_우선한다():
    person = Participant("p1", "가나다", Gender.MALE, "A관", grade=Grade(3), age=15)
    assert resolve_grade(person).label == "초3"


def test_학년이_없으면_나이로_계산한다():
    person = Participant("p1", "가나다", Gender.MALE, "A관", age=15)
    assert resolve_grade(person).label == "중2"


def test_도장키는_공백을_무시한다():
    assert dojang_key(" 광명 검도관 ") == dojang_key("광명검도관")


def test_운영자가_묶은_도장은_대표키로_모인다():
    aliases = {"광명검도장": "광명검도관"}
    assert dojang_key("광명 검도장", aliases) == dojang_key("광명검도관", aliases)


@pytest.mark.parametrize(
    ("school", "grade", "label"),
    [
        ("철산초등학교", "3", "초3"),
        ("하안초", "3학년", "초3"),
        ("광명중학교", "2", "중2"),
        ("소하중", "1", "중1"),
        ("광명고등학교", "3", "고3"),
        ("명문고", "1학년", "고1"),
        ("", "초4", "초4"),
        ("철산초등학교", "초5", "초5"),
        ("", "일반", "성인"),
    ],
)
def test_학교_칸과_학년_숫자를_함께_읽는다(school, grade, label):
    assert parse_school_grade(school, grade).label == label


@pytest.mark.parametrize(("school", "grade"), [("", "3"), ("검도대학원", "3"), ("철산초등학교", "7"), ("광명중학교", "")])
def test_학교급을_알_수_없거나_학년이_틀리면_None(school, grade):
    assert parse_school_grade(school, grade) is None
