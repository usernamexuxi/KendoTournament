from kendo_tournament.application.draw_brackets import draw_all, rebuild_divisions
from kendo_tournament.application.print_booklet import (
    booklet_pages,
    move_in_order,
    print_order,
    reset_print_order,
    section_title,
    set_print_order,
    toggle_page_break,
)
from kendo_tournament.domain.model import DivisionRule, Event, Gender, Grade, Participant, Team
from kendo_tournament.domain.tournament import Tournament


def tournament():
    t = Tournament("시험")
    grades = {Gender.MALE: (1, 1, 2, 2, 7, 7, 13, 13), Gender.FEMALE: (1, 1, 2, 2)}
    t.participants = [
        Participant(f"{gender.name}{i}", f"선수{i}", gender, f"도장{i % 3}", grade=Grade(g))
        for gender, values in grades.items()
        for i, g in enumerate(values)
    ]
    t.rules = [
        DivisionRule("성인", Event.INDIVIDUAL, Gender.MALE, Grade(13), Grade(13)),
        DivisionRule("여1", Event.INDIVIDUAL, Gender.FEMALE, Grade(1), Grade(1)),
        DivisionRule("여2", Event.INDIVIDUAL, Gender.FEMALE, Grade(2), Grade(2)),
        DivisionRule("남중", Event.INDIVIDUAL, Gender.MALE, Grade(7), Grade(9)),
        DivisionRule("남1", Event.INDIVIDUAL, Gender.MALE, Grade(1), Grade(1)),
        DivisionRule("남2", Event.INDIVIDUAL, Gender.MALE, Grade(2), Grade(2)),
    ]
    rebuild_divisions(t)
    draw_all(t)
    return t


def test_쪽_제목은_학교급과_성별이다():
    t = tournament()
    titles = {d.label: section_title(t, d) for d in t.divisions}
    assert titles["남자 초1 개인전"] == "초등부 남자"
    assert titles["여자 초2 개인전"] == "초등부 여자"
    assert titles["남자 중1~중3 개인전"] == "중등부 남자"
    assert titles["남자 성인 개인전"] == "성인부 남자"


def test_기본_인쇄_순서는_학교급_성별_학년_순이고_남자가_먼저다():
    assert print_order(tournament()) == [
        "남자 초1 개인전",
        "남자 초2 개인전",
        "여자 초1 개인전",
        "여자 초2 개인전",
        "남자 중1~중3 개인전",
        "남자 성인 개인전",
    ]


def test_순서를_옮기면_그_순서로_찍히고_새로_생긴_부문은_뒤에_붙는다():
    t = tournament()
    move_in_order(t, "남자 초2 개인전", -1)
    assert print_order(t)[:2] == ["남자 초2 개인전", "남자 초1 개인전"]
    move_in_order(t, "남자 초2 개인전", -1)
    assert print_order(t)[0] == "남자 초2 개인전"
    t.print_order = ["남자 성인 개인전"]
    assert print_order(t)[0] == "남자 성인 개인전"
    assert len(print_order(t)) == len(t.divisions)


def test_끌어_옮긴_순서를_그대로_저장하고_기본_순서로_되돌릴_수_있다():
    t = tournament()
    default = print_order(t)
    wanted = [default[-1], *default[:-1]]
    set_print_order(t, wanted)
    assert print_order(t) == wanted
    reset_print_order(t)
    assert print_order(t) == default


def test_새_쪽을_정하면_쪽이_늘고_다시_누르면_풀린다():
    t = tournament()
    labels = ["남자 초1 개인전", "남자 초2 개인전"]
    assert len(booklet_pages(t, labels)) == 1
    toggle_page_break(t, "남자 초2 개인전")
    assert len(booklet_pages(t, labels)) == 2
    toggle_page_break(t, "남자 초2 개인전")
    assert len(booklet_pages(t, labels)) == 1


def test_인쇄_순서대로_부문_띠가_실린다():
    t = tournament()
    pages = booklet_pages(t, print_order(t))
    order = print_order(t)
    shown = [x.text for page in pages for x in sorted(page.texts, key=lambda x: x.y) if x.text in order]
    assert shown == order


def _team_tournament(team_count: int = 3):
    t = Tournament("시험")
    t.participants = [
        Participant(f"p{i}", f"선수{i}", Gender.MALE, f"도장{i // 3}", grade=Grade(8)) for i in range(3 * team_count)
    ]
    t.teams = [
        Team(f"t{k}", f"도장{k} A", f"도장{k}", tuple(f"p{i}" for i in range(3 * k, 3 * k + 3))) for k in range(team_count)
    ]
    t.rules = [DivisionRule("단", Event.TEAM, Gender.MALE, Grade(7), Grade(12), team_size=3)]
    rebuild_divisions(t)
    draw_all(t)
    return t


def _member_lines_under_boxes(page):
    """팀 이름(칸) 글자마다 바로 아래, 같은 가로 자리에 있는 팀원 줄."""
    boxes = [x for x in page.texts if x.slot is not None]
    found = {}
    for box in boxes:
        below = [x for x in page.texts if x.slot is None and 0 < x.y - box.y < 9 and abs(x.x - box.x) < 1]
        found[box.text] = [x.text for x in below]
    return found


def test_단체전_팀_상자_밑에는_팀원_이름이_빠짐없이_들어간다():
    t = _team_tournament()
    pages = booklet_pages(t, [d.label for d in t.divisions])
    found = {}
    for page in pages:
        found |= _member_lines_under_boxes(page)
    assert found == {
        "도장0A": ["선수0 · 선수1 · 선수2"],
        "도장1A": ["선수3 · 선수4 · 선수5"],
        "도장2A": ["선수6 · 선수7 · 선수8"],
    }
    texts = [x.text for page in pages for x in page.texts]
    assert "팀 명단" not in texts


def test_팀원_이름_넣기를_끄면_팀_이름만_싣는다():
    from dataclasses import replace

    t = _team_tournament()
    t.book = replace(t.book, team_members=False)
    pages = booklet_pages(t, [d.label for d in t.divisions])
    texts = [x.text for page in pages for x in page.texts]
    assert "도장0A" in texts
    assert not any("선수" in text for text in texts)


def test_단체전이_한_쪽에_몰려도_팀원_줄이_아래_상자와_겹치지_않는다():
    t = Tournament("몰림")
    groups = [(Gender.MALE, 7), (Gender.FEMALE, 7), (Gender.MALE, 13), (Gender.FEMALE, 13)]
    for g, (gender, grade) in enumerate(groups):
        for k in range(8):
            ids = tuple(f"p{g}{k}{m}" for m in range(3))
            t.participants += [Participant(i, f"선수{i}", gender, f"도장{g}{k}", grade=Grade(grade)) for i in ids]
            t.teams.append(Team(f"t{g}{k}", f"도장{g}{k} A", f"도장{g}{k}", ids))
        last = 12 if grade == 7 else 13
        t.rules.append(DivisionRule(f"단{g}", Event.TEAM, gender, Grade(grade), Grade(last), team_size=3))
    rebuild_divisions(t)
    draw_all(t)
    pages = booklet_pages(t, [d.label for d in t.divisions])
    member_count = 0
    for page in pages:
        boxes = [x for x in page.texts if x.slot is not None]
        members = [x for x in page.texts if x.text.startswith("선수")]
        member_count += len(members)
        for member in members:
            below = [b.y for b in boxes if abs(b.x - member.x) < 1 and b.y > member.y]
            if below:
                # 아래 상자(최대 8mm 높이)의 윗변보다 팀원 줄 글자(8.5pt ≈ 3mm)의 아랫변이 위에 있어야 한다.
                assert min(below) - 4.0 > member.y + 1.5
    assert member_count == 32


def test_단체전은_개인전을_다_실은_뒤_맨_뒤에_나온다():
    from kendo_tournament.domain.model import Team

    t = tournament()
    t.teams = [Team("팀1", "도장0 A", "도장0", ("MALE0", "MALE1")), Team("팀2", "도장1 A", "도장1", ("MALE2", "MALE3"))]
    t.rules.append(DivisionRule("단초", Event.TEAM, Gender.MALE, Grade(1), Grade(6), team_size=2))
    rebuild_divisions(t)
    events = {d.label: d.event for d in t.divisions}
    order = [events[label] for label in print_order(t)]
    assert Event.TEAM in order
    assert order == sorted(order, key=lambda event: event is Event.TEAM)


def _catalog_tournament():
    """참고 책자(제26회 광명시장기 카탈로그) 8·9쪽에 실린 부문들을 흉내 낸 대회."""
    t = Tournament("책자")
    people = [
        (Gender.MALE, 1), (Gender.FEMALE, 1), (Gender.FEMALE, 7), (Gender.MALE, 7),
        (Gender.MALE, 10), (Gender.MALE, 13), (Gender.FEMALE, 13),
    ]  # fmt: skip
    t.participants = [
        Participant(f"p{i}{k}", f"선수{i}{k}", gender, f"도장{k}", grade=Grade(grade), age=40 if grade == 13 else None)
        for i, (gender, grade) in enumerate(people)
        for k in range(2)
    ]
    t.teams = [Team(f"t{i}{k}", f"도장{k} A", f"도장{k}", (f"p{i}{k}",)) for i in (0, 1, 2, 3, 5, 6) for k in range(2)]
    rules = [
        ("여일반", Event.INDIVIDUAL, Gender.FEMALE, 13, 13),
        ("남장년", Event.INDIVIDUAL, Gender.MALE, 13, 13),
        ("남고", Event.INDIVIDUAL, Gender.MALE, 10, 12),
        ("남중", Event.INDIVIDUAL, Gender.MALE, 7, 9),
        ("여청소년", Event.INDIVIDUAL, Gender.FEMALE, 7, 12),
        ("여초", Event.INDIVIDUAL, Gender.FEMALE, 1, 3),
        ("남초", Event.INDIVIDUAL, Gender.MALE, 1, 1),
        ("남일반단", Event.TEAM, Gender.MALE, 13, 13),
        ("여일반단", Event.TEAM, Gender.FEMALE, 13, 13),
        ("남청소년단", Event.TEAM, Gender.MALE, 7, 12),
        ("여청소년단", Event.TEAM, Gender.FEMALE, 7, 12),
        ("남초단", Event.TEAM, Gender.MALE, 1, 2),
        ("여초단", Event.TEAM, Gender.FEMALE, 1, 3),
    ]
    t.rules = [DivisionRule(rid, ev, g, Grade(a), Grade(b), team_size=1) for rid, ev, g, a, b in rules]
    rebuild_divisions(t)
    return t


def test_기본_인쇄_순서는_학교급을_지키고_그_안에서_남자_종별이_먼저다():
    """운영자: 「남자 먼저 하고 여자. 초등부·중등부·고등부·중고등부는 지키고」 — 개인전·단체전 모두."""
    order = print_order(_catalog_tournament())
    assert order == [
        "남자 초1 개인전",
        "여자 초1~초3 개인전",
        "남자 중1~중3 개인전",
        "여자 중1~고3 개인전",
        "남자 고1~고3 개인전",
        "남자 성인 개인전",
        "여자 성인 개인전",
        "남자 초1~초2 단체전",
        "여자 초1~초3 단체전",
        "남자 중1~고3 단체전",
        "여자 중1~고3 단체전",
        "남자 성인 단체전",
        "여자 성인 단체전",
    ]


def test_성인_나이_구간은_청년_장년_중년_순서로_찍힌다():
    t = Tournament("나이")
    t.participants = [
        Participant(f"p{age}{k}", f"선수{age}{k}", Gender.MALE, f"도장{k}", grade=Grade(13), age=age)
        for age in (50, 40, 25)
        for k in range(2)
    ]
    t.rules = [
        DivisionRule("중년", Event.INDIVIDUAL, Gender.MALE, Grade(13), Grade(13), age_from=48, age_name="중년부"),
        DivisionRule("청년", Event.INDIVIDUAL, Gender.MALE, Grade(13), Grade(13), age_from=20, age_to=35, age_name="청년부"),
        DivisionRule("장년", Event.INDIVIDUAL, Gender.MALE, Grade(13), Grade(13), age_from=36, age_to=47, age_name="장년부"),
    ]
    rebuild_divisions(t)
    assert [label.split("(")[0] for label in print_order(t)] == ["남자 청년부", "남자 장년부", "남자 중년부"]


def test_한_명_한_팀뿐인_부문은_인쇄_순서와_책자에서_빠진다():
    """운영자: 「단독 출전이라는 건 없다, 빼는 거다」. 경기가 없는 부문은 대진표를 싣지 않는다."""
    t = _team_tournament(team_count=1)
    alone = [d.label for d in t.divisions if len(d.entries) == 1]
    assert alone, "시험 전제: 한 팀뿐인 부문이 있어야 한다"
    assert not set(alone) & set(print_order(t))
    pages = booklet_pages(t, [d.label for d in t.divisions])
    assert not any("단독 출전" in text.text for page in pages for text in page.texts)


def _entry_numbers(pages):
    from kendo_tournament.domain.layout.bracket_boxes import ENTRY_NUMBER_COLOR

    return [int(t.text) for page in pages for t in page.texts if t.color == ENTRY_NUMBER_COLOR]


def _expected_per_division(t, labels):
    divisions = {d.label: d for d in t.divisions}
    return [n for label in labels for n in range(1, len(divisions[label].entries) + 1)]


def test_대진표_이름_옆_번호는_종별마다_1부터_다시_센다():
    """운영자: 여자 초등 1~3학년부를 1부터 매기면, 그 뒤 여자 초등 4~6학년부는 다시 1부터."""
    t = tournament()
    labels = print_order(t)
    numbers = _entry_numbers(booklet_pages(t, labels))
    assert numbers == _expected_per_division(t, labels)


def test_단체전_번호도_종별마다_1부터_센다():
    t = tournament()
    t.teams = [Team("팀1", "도장0 A", "도장0", ("MALE0", "MALE1")), Team("팀2", "도장1 A", "도장1", ("MALE2", "MALE3"))]
    t.rules.append(DivisionRule("단초", Event.TEAM, Gender.MALE, Grade(1), Grade(6), team_size=2))
    rebuild_divisions(t)
    draw_all(t)
    labels = print_order(t)
    numbers = _entry_numbers(booklet_pages(t, labels))
    assert numbers == _expected_per_division(t, labels)
