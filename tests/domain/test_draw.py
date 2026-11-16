import random

import pytest

from kendo_tournament.domain.draw.bracket import bracket_size, first_meeting_round
from kendo_tournament.domain.draw.draw import draw_bracket, spread_order
from kendo_tournament.domain.draw.validate import first_match_conflicts, same_dojang_pairs
from kendo_tournament.domain.model import Entry


def make_entries(dojang_sizes):
    entries = []
    for d, count in enumerate(dojang_sizes):
        for k in range(count):
            entries.append(Entry(f"{d}-{k}", f"선수{d}-{k}", f"도장{d}"))
    return entries


def first_match_count(bracket):
    """양쪽 하위 대진에 선수가 한 명씩뿐인 경기 수. 부전승 자리로 정해지므로 배치와 무관하다."""
    count = 0
    block = 2
    while block <= bracket.size:
        half = block // 2
        for start in range(0, bracket.size, block):
            if bracket.count_in(start, half) == 1 and bracket.count_in(start + half, half) == 1:
                count += 1
        block *= 2
    return count


def pass_count(bracket):
    """한쪽이 비어 상대 없이 올라가는(부전승) 자리 수."""
    count = 0
    block = 2
    while block <= bracket.size:
        half = block // 2
        for start in range(0, bracket.size, block):
            sides = (bracket.count_in(start, half), bracket.count_in(start + half, half))
            if 0 in sides and sides != (0, 0):
                count += 1
        block *= 2
    return count


def fewest_passes(n):
    """라운드마다 남은 사람이 홀수일 때만 한 명이 쉰다 — 그보다 적을 수는 없다."""
    passes = 0
    while n > 1:
        passes += n % 2
        n = (n + 1) // 2
    return passes


def avoidable(dojang_sizes, bracket):
    f = first_match_count(bracket)
    return sum(min(c, f) for c in dojang_sizes) >= 2 * f


@pytest.mark.parametrize(("n", "size"), [(1, 1), (2, 2), (3, 4), (5, 8), (26, 32), (64, 64), (65, 128)])
def test_대진_크기는_2의_거듭제곱(n, size):
    assert bracket_size(n) == size


def test_만나는_라운드():
    assert first_meeting_round(0, 1) == 1
    assert first_meeting_round(0, 2) == 2
    assert first_meeting_round(0, 31) == 5


def test_퍼짐_순서는_절반을_번갈아_간다():
    assert spread_order(4) == [0, 2, 1, 3]


def test_무작위_구성_300가지에서_규칙을_지킨다():
    rng = random.Random(7)
    for case in range(300):
        n = rng.randint(1, 64)
        sizes = []
        remaining = n
        while remaining:
            take = rng.randint(1, max(1, min(remaining, rng.choice([1, 2, 3, 5, n]))))
            sizes.append(take)
            remaining -= take
        entries = make_entries(sizes)
        bracket = draw_bracket(entries, "시험", seed=case)

        assert bracket.size == bracket_size(n)
        assert sorted(e.id for e in bracket.entries) == sorted(e.id for e in entries)
        assert pass_count(bracket) == fewest_passes(n), f"부전승이 더 줄 수 있음: {n}명"
        if avoidable(sizes, bracket):
            assert first_match_conflicts(bracket) == [], f"분리 가능한데 충돌: {sizes}"


@pytest.mark.parametrize("n", [2, 4, 6, 10, 12, 14, 26, 30, 62])
def test_선수가_짝수면_1회전에_부전승_없이_모두_경기한다(n):
    for seed in range(10):
        bracket = draw_bracket(make_entries([1] * n), "t", seed)
        for unit in range(0, bracket.size, 2):
            pair = (bracket.slots[unit] is None, bracket.slots[unit + 1] is None)
            assert pair in ((False, False), (True, True)), f"{n}명 1회전에 부전승"


def test_6명이면_1회전_3경기_뒤_한_명만_한_번_쉰다():
    bracket = draw_bracket(make_entries([1] * 6), "t", 1)
    assert first_match_count(bracket) == 3
    assert pass_count(bracket) == 1


def test_같은_seed면_같은_대진():
    entries = make_entries([4, 3, 3, 2, 1])
    assert draw_bracket(entries, "t", 42).slots == draw_bracket(entries, "t", 42).slots


def test_다른_seed면_대개_다른_대진():
    entries = make_entries([1] * 16)
    results = {draw_bracket(entries, "t", seed).slots for seed in range(5)}
    assert len(results) > 1


def test_한_도장_두명은_결승에서_만난다():
    entries = make_entries([2, 1, 1, 1, 1, 1, 1])
    for seed in range(20):
        bracket = draw_bracket(entries, "t", seed)
        ((_, _, meet_round),) = same_dojang_pairs(bracket)
        assert meet_round == bracket.rounds


def test_한_도장이_절반을_넘으면_피할수_없는_충돌만_남는다():
    entries = make_entries([6, 1, 1])
    bracket = draw_bracket(entries, "t", 1)
    assert len(first_match_conflicts(bracket)) == 2


def test_단독_출전():
    bracket = draw_bracket(make_entries([1]), "t", 1)
    assert bracket.size == 1 and bracket.slots[0] is not None


def test_출전자가_없으면_거부():
    with pytest.raises(ValueError):
        draw_bracket([], "t", 1)


def test_사람이_더_많은_절반은_늘_오른쪽이다():
    from kendo_tournament.domain.draw.draw import draw_bracket as draw
    from kendo_tournament.domain.model import Entry as E

    for count in (3, 5, 10, 11, 21, 22, 37):
        for seed in range(5):
            bracket = draw([E(str(i), f"선수{i}", f"도장{i % 4}") for i in range(count)], "부문", seed)
            half = bracket.size // 2
            left = sum(e is not None for e in bracket.slots[:half])
            right = sum(e is not None for e in bracket.slots[half:])
            assert left <= right, (count, seed)
