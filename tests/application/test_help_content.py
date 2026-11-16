from kendo_tournament.application.help_content import SECTIONS, emphasized_parts


def test_낫표_안의_단추_이름만_굵게_나눈다():
    assert emphasized_parts("「모두 추첨」을 누르고 「저장」") == [
        ("「", False),
        ("모두 추첨", True),
        ("」을 누르고 「", False),
        ("저장", True),
        ("」", False),
    ]
    assert emphasized_parts("굵은 곳 없음") == [("굵은 곳 없음", False)]


def test_도움말_줄은_한_가지씩_짧게_쓴다():
    lines = [line for section in SECTIONS for group in section.groups for line in group.lines]
    assert lines
    assert all(len(line) <= 90 for line in lines), [line for line in lines if len(line) > 90]
    assert all(section.summary for section in SECTIONS)
