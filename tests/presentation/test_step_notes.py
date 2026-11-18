import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QListWidget  # noqa: E402

from kendo_tournament.application.step_progress import StepNote  # noqa: E402
from kendo_tournament.presentation.step_notes import show_step_notes  # noqa: E402

APP = QApplication.instance() or QApplication([])
STEPS = ("① 가", "② 나", "③ 다")


def test_진행_표시는_단계_이름_밑_줄에_붙는다():
    steps = QListWidget()
    steps.resize(400, 400)
    steps.addItems(STEPS)
    show_step_notes(steps, STEPS, (StepNote("대회", True), StepNote("", False), StepNote("3/16개 짬", False)))
    assert steps.item(0).text() == "① 가\n      ✓ 대회"
    assert steps.item(1).text() == "② 나"
    assert steps.item(2).text().endswith("3/16개 짬")


def test_긴_대회_이름은_메뉴_폭에_맞게_줄이고_가로_스크롤을_만들지_않는다():
    from PySide6.QtCore import Qt

    steps = QListWidget()
    steps.resize(210, 400)
    steps.addItems(STEPS)
    long_name = "제19회 광명시회장기 검도대회 겸 생활체육 검도 한마당"
    show_step_notes(steps, STEPS, (StepNote(long_name, True), StepNote("", False), StepNote("", False)))
    note = steps.item(0).text().splitlines()[1]
    assert note.strip().endswith("…") and long_name not in note
    assert steps.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
