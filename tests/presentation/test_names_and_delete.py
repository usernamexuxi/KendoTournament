import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from kendo_tournament.application.tournament_session import TournamentSession  # noqa: E402
from kendo_tournament.domain.division.category_table import TEMPLATES  # noqa: E402
from kendo_tournament.domain.division.presets import PresetChoice  # noqa: E402
from kendo_tournament.domain.model import Event, Gender, Grade, Participant  # noqa: E402
from kendo_tournament.infrastructure.readers.registry import reader_for  # noqa: E402
from kendo_tournament.infrastructure.storage.json_repository import JsonTournamentRepository  # noqa: E402
from kendo_tournament.presentation.division_view import FROM, DivisionView  # noqa: E402
from kendo_tournament.presentation.roster_view import RosterView  # noqa: E402

APP = QApplication.instance() or QApplication([])


def _session(tmp_path):
    s = TournamentSession(JsonTournamentRepository(), reader_for, tmp_path)
    people = [
        Participant(f"p{i}", f"선수{i}", Gender.MALE, f"도장{i}", Grade(1 + i % 3), None, "광명", "a.docx") for i in range(4)
    ]
    s.set_participants(people)
    return s


def _answer(monkeypatch, button):
    asked: list[str] = []

    def question(*args, **kwargs):
        asked.append(args[2])
        return button

    monkeypatch.setattr(QMessageBox, "question", question)
    return asked


def test_고른_선수_지우기는_한_번_묻고_아니요면_그대로_둔다(tmp_path, monkeypatch):
    s = _session(tmp_path)
    view = RosterView(s, (".docx",))
    before = len(s.tournament.participants)
    view._table.selectRow(0)
    asked = _answer(monkeypatch, QMessageBox.StandardButton.No)
    view._remove_selected()
    assert asked
    assert len(s.tournament.participants) == before
    _answer(monkeypatch, QMessageBox.StandardButton.Yes)
    view._remove_selected()
    assert len(s.tournament.participants) == before - 1


def test_기준_표를_거쳐_나눠도_요강_이름이_남고_학년을_고치면_뗀다(tmp_path):
    s = _session(tmp_path)
    s.set_categories(TEMPLATES["초등 저학년·고학년부"])
    view = DivisionView(s, (".docx",))
    view._add_preset(PresetChoice((Event.INDIVIDUAL,)))
    view._apply()
    assert "남자 초등 저학년부 개인전" in [d.label for d in s.tournament.divisions]
    view._table.cellWidget(0, FROM).select(Grade(2))
    view._apply()
    labels = [d.label for d in s.tournament.divisions]
    assert "남자 초등 저학년부 개인전" not in labels
    assert any("초2~초3" in label for label in labels)
