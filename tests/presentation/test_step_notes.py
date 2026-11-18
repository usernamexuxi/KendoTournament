import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QListWidget  # noqa: E402

from kendo_tournament.application.step_progress import StepNote  # noqa: E402
from kendo_tournament.presentation.step_notes import show_step_notes  # noqa: E402

APP = QApplication.instance() or QApplication([])
STEPS = ("① 가", "② 나", "③ 다")


def test_진행_표시는_단계_이름_밑_줄에_붙는다():
    steps = QListWidget()
    steps.addItems(STEPS)
    show_step_notes(steps, STEPS, (StepNote("대회", True), StepNote("", False), StepNote("할 차례", False)))
    assert steps.item(0).text() == "① 가\n      ✓ 대회"
    assert steps.item(1).text() == "② 나"
    assert steps.item(2).text().endswith("할 차례")
