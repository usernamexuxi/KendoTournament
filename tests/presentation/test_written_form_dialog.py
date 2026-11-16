import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from kendo_tournament.application.tournament_session import TournamentSession  # noqa: E402
from kendo_tournament.infrastructure.readers.registry import reader_for  # noqa: E402
from kendo_tournament.infrastructure.storage.json_repository import JsonTournamentRepository  # noqa: E402
from kendo_tournament.presentation.written_form_dialog import WrittenFormDialog  # noqa: E402

APP = QApplication.instance() or QApplication([])


def session(tmp_path):
    s = TournamentSession(JsonTournamentRepository(), reader_for, tmp_path)
    s.new("시험 대회")
    return s


def test_종별_줄에_적은_이름과_팀_자리가_명단에_들어간다(tmp_path):
    s = session(tmp_path)
    parent = QWidget()
    dialog = WrittenFormDialog(s, parent)
    dialog._dojang.setCurrentText("누리검도관")
    first_label = next(iter(dialog._individual))
    dialog._individual[first_label].setText("김하나, 이두리")
    _, _, names = dialog._teams._rows[0]
    names[0].setText("오가온")
    names[2].setText("윤마루")
    dialog.accept()
    assert dialog.result() == WrittenFormDialog.DialogCode.Accepted
    individuals = [p for p in s.tournament.participants if p.category == first_label]
    assert sorted(p.name for p in individuals) == ["김하나", "이두리"]
    (team,) = s.tournament.teams
    assert team.positions == ("선봉", "주장")
    assert first_label == "남초등 1학년", "광명 기본 종별 「남초등 1~2학년」이 학년마다 한 줄로 나뉜다"


def test_도장을_안_적으면_창을_닫지_않고_명단도_그대로다(tmp_path, monkeypatch):
    from kendo_tournament.presentation import written_form_dialog

    shown: list[str] = []
    monkeypatch.setattr(written_form_dialog.QMessageBox, "warning", lambda parent, title, text: shown.append(text))
    s = session(tmp_path)
    parent = QWidget()
    dialog = WrittenFormDialog(s, parent)
    dialog._individual[next(iter(dialog._individual))].setText("김하나")
    dialog.accept()
    assert shown and dialog.result() != WrittenFormDialog.DialogCode.Accepted
    assert s.tournament.participants == []
