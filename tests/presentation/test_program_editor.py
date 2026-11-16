import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTabWidget, QWidget  # noqa: E402

from kendo_tournament.domain.greeting import Greeting  # noqa: E402
from kendo_tournament.domain.ports import ExportError  # noqa: E402
from kendo_tournament.domain.program import DEFAULT_PROGRAM, ProgramContent  # noqa: E402
from kendo_tournament.presentation import greeting_dialog  # noqa: E402
from kendo_tournament.presentation.greeting_dialog import GreetingDialog  # noqa: E402
from kendo_tournament.presentation.program_editor import ProgramEditor  # noqa: E402
from kendo_tournament.presentation.program_rows_table import ProgramRowsTable  # noqa: E402

APP = QApplication.instance() or QApplication([])


GREETING = Greeting(body="대회사 본문", date_text="2026. 4. 12", position="관장", name="홍길동", photo_file="")


def test_식순_창은_고치지_않고_저장하면_내용이_그대로_넘어가고_대회사_탭은_없다():
    saved: list[ProgramContent] = []
    parent = QWidget()
    editor = ProgramEditor(DEFAULT_PROGRAM, saved.append, parent)
    editor.accept()
    assert saved == [DEFAULT_PROGRAM]
    assert editor.result() == ProgramEditor.DialogCode.Accepted
    tabs = editor.findChild(QTabWidget)
    assert "대회사" not in [tabs.tabText(i) for i in range(tabs.count())]


def test_대회사_창은_고치지_않고_저장하면_대회사가_그대로_넘어간다():
    saved: list[Greeting] = []
    parent = QWidget()
    dialog = GreetingDialog(GREETING, saved.append, parent)
    dialog.accept()
    assert saved == [GREETING]
    assert dialog.result() == GreetingDialog.DialogCode.Accepted


def test_대회사_저장이_ExportError_를_내면_알리고_창을_닫지_않는다(monkeypatch):
    def fail(greeting: Greeting) -> None:
        raise ExportError("사진을 읽지 못했습니다.")

    reported: list[ExportError] = []
    monkeypatch.setattr(greeting_dialog, "report_error", lambda parent, error: reported.append(error))
    parent = QWidget()
    dialog = GreetingDialog(GREETING, fail, parent)
    dialog.accept()
    assert len(reported) == 1
    assert dialog.result() != GreetingDialog.DialogCode.Accepted


def test_줄을_추가하면_고른_줄_아래에_생기고_빈_줄은_저장되지_않는다():
    table = ProgramRowsTable(("순서", "진행"), [("개회식통보", "사회자"), ("국민의례", "사회자")])
    table._table.setCurrentCell(0, 0)
    table._add_row()
    assert table._table.currentRow() == 1
    assert table.values() == [("개회식통보", "사회자"), ("국민의례", "사회자")]
    table._table.item(1, 0).setText("내빈소개")
    assert table.values()[1] == ("내빈소개", "")


def test_위로_아래로_줄을_옮긴다():
    table = ProgramRowsTable(("수칙",), [("가",), ("나",), ("다",)])
    table._table.setCurrentCell(2, 0)
    table._move(-1)
    assert table.values() == [("가",), ("다",), ("나",)]
    table._move(-1)
    table._move(-1)
    assert table.values() == [("다",), ("가",), ("나",)]
