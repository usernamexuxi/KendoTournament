from datetime import datetime, timedelta, timezone

from kendo_tournament.application.draw_brackets import draw_all, rebuild_divisions
from kendo_tournament.application.step_progress import DONE, TODO, saved_text, step_notes
from tests.application.test_print_booklet import tournament

KST = timezone(timedelta(hours=9))
ROSTER, DIVISIONS, BRACKETS = 1, 2, 3


def test_빈_대회는_명단이_할_차례이고_뒤_단계는_조용하다():
    from kendo_tournament.domain.tournament import Tournament

    notes = step_notes(Tournament("새 대회"))
    assert str(notes[ROSTER]) == TODO
    assert not notes[ROSTER].done
    assert str(notes[DIVISIONS]) == "" and str(notes[BRACKETS]) == ""


def test_명단만_있으면_종별_나누기가_할_차례다():
    t = tournament()
    t.divisions = []
    t.brackets = {}
    notes = step_notes(t)
    assert notes[ROSTER].done and str(notes[ROSTER]).startswith(DONE)
    assert str(notes[DIVISIONS]) == TODO


def test_대진을_다_짜면_대진_단계에_체크가_붙고_일부만_짜면_몇_개인지_보인다():
    t = tournament()
    rebuild_divisions(t)
    draw_all(t)
    assert step_notes(t)[BRACKETS].done
    first = t.divisions[0].label
    del t.brackets[first]
    partly = step_notes(t)[BRACKETS]
    assert not partly.done
    assert f"/{len(t.divisions)}" in str(partly)


def test_저장_알림은_경로가_아니라_시각과_파일_이름이다():
    text = saved_text(datetime(2026, 11, 18, 15, 7, tzinfo=KST), "대회.kendo", opened=True)
    assert text.startswith(DONE)
    assert "오후 3:07" in text and "대회.kendo" in text and "\\" not in text
    assert "오전 12:05" in saved_text(datetime(2026, 11, 18, 0, 5, tzinfo=KST), "a.kendo", opened=False)
    assert "열어 둠" in saved_text(None, "a.kendo", opened=True)
    assert "저장 전" in saved_text(None, "a.kendo", opened=False)
