import pytest

from kendo_tournament.domain.draw.bracket import Bracket
from kendo_tournament.domain.draw.editing import insert_entry, recommend_insert_slots, swap_slots, withdraw
from kendo_tournament.domain.draw.numbering import Leaf, number_matches
from kendo_tournament.domain.model import Entry

_ = None


def entry(n, dojang=None):
    return Entry(str(n), f"선수{n}", dojang or f"도장{n}")


def example_b_group():
    """개발자가 보낸 「남자 단부 개인전 B조」(26명) 예시와 같은 배치. 숫자는 예시의 선수 번호다."""
    left = [27, _, 28, 29, 30, 31, 32, _, 33, _, 34, 35, 36, 37, 38, 39]
    right = [40, _, 41, 42, 43, 44, 45, _, 46, _, 47, 48, 49, 50, 51, 52]
    return Bracket("남자 단부 개인전 B조", tuple(entry(n) if n else None for n in left + right), 0)


def players_of(node):
    if isinstance(node, Leaf):
        return []
    return [node.top, node.bottom]


def leaf_names(bracket, node):
    return {bracket.slots[child.slot].name for child in players_of(node) if isinstance(child, Leaf)}


def test_예시_B조와_같은_순서로_경기번호를_매긴다():
    bracket = example_b_group()
    numbered = number_matches(bracket)
    by_number = {m.number: m for m in numbered.matches}

    assert sorted(by_number) == list(range(1, 26))
    expected_first_round = {
        1: {"선수28", "선수29"},
        2: {"선수30", "선수31"},
        3: {"선수34", "선수35"},
        4: {"선수36", "선수37"},
        5: {"선수38", "선수39"},
        6: {"선수41", "선수42"},
        7: {"선수43", "선수44"},
        8: {"선수47", "선수48"},
        9: {"선수49", "선수50"},
        10: {"선수51", "선수52"},
    }
    for number, names in expected_first_round.items():
        assert leaf_names(bracket, by_number[number]) == names
    assert leaf_names(bracket, by_number[11]) == {"선수27"}
    assert by_number[11].bottom == by_number[1]
    assert by_number[19].top == by_number[11] and by_number[19].bottom == by_number[12]
    assert by_number[23].top == by_number[19] and by_number[23].bottom == by_number[20]
    assert by_number[24].top == by_number[21] and by_number[24].bottom == by_number[22]
    assert numbered.final is by_number[25] or numbered.final == by_number[25]


def test_결승은_마지막_번호이고_번호가_빠짐없이_이어진다():
    for count in (3, 4, 5, 6, 13):
        numbered = number_matches(Bracket("t", tuple(entry(n) for n in range(count)) + (None,) * (16 - count), 0))
        numbers = sorted(m.number for m in numbered.matches)
        assert numbers == list(range(1, count))
        assert numbered.final.number == count - 1


def test_8강_번호():
    bracket = Bracket("t", tuple(entry(n) for n in range(8)), 0)
    numbered = number_matches(bracket)
    first_round = [m for m in numbered.matches if m.round == 1]
    assert [(m.number, m.start) for m in first_round] == [(1, 0), (2, 2), (3, 4), (4, 6)]
    assert [m.number for m in numbered.matches if m.round == 2] == [5, 6]
    assert numbered.final.number == 7


def test_두명이면_결승_한경기():
    numbered = number_matches(Bracket("t", (entry(1), entry(2)), 0))
    assert [m.number for m in numbered.matches] == [1]


def test_한명이면_경기가_없다():
    numbered = number_matches(Bracket("t", (entry(1),), 0))
    assert numbered.matches == () and isinstance(numbered.root, Leaf)


def test_기권으로_한_묶음이_통째로_비면_상대가_그냥_올라간다():
    bracket = Bracket("t", tuple(entry(n) for n in range(8)), 0)
    bracket = withdraw(withdraw(bracket, 0), 1)
    numbered = number_matches(bracket)
    assert [m.number for m in numbered.matches] == [1, 2, 3, 4, 5]
    assert numbered.final.top.number == 1
    assert numbered.final.bottom.number == 4


def test_기권과_끼워넣기는_다른_칸을_건드리지_않는다():
    bracket = example_b_group()
    after = insert_entry(withdraw(bracket, 2), 2, entry(99))
    changed = [i for i in range(bracket.size) if bracket.slots[i] != after.slots[i]]
    assert changed == [2]


def test_빈칸이_아니면_끼워넣을_수_없다():
    with pytest.raises(ValueError):
        insert_entry(example_b_group(), 0, entry(99))


def test_같은_선수를_두번_넣을_수_없다():
    with pytest.raises(ValueError):
        insert_entry(example_b_group(), 1, entry(28))


def test_맞바꾸기():
    bracket = swap_slots(example_b_group(), 0, 2)
    assert bracket.slots[0].name == "선수28" and bracket.slots[2].name == "선수27"


def test_끼워넣기_추천은_같은_도장과_늦게_만나는_칸이_먼저():
    bracket = example_b_group()
    newcomer = entry(99, dojang="도장27")
    best = recommend_insert_slots(bracket, newcomer)[0]
    assert best >= 16
