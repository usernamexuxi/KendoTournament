import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QListWidget  # noqa: E402

from kendo_tournament.application.step_progress import StepNote  # noqa: E402
from kendo_tournament.presentation.step_nav import StepNav, show_step_notes  # noqa: E402

APP = QApplication.instance() or QApplication([])
STEPS = ("① 가", "② 나", "③ 다")


def test_다음_단추는_다음_단계_이름을_보여_주고_누르면_그_단계로_간다():
    nav = StepNav(STEPS)
    gone: list[int] = []
    nav.go.connect(gone.append)
    nav.show_step(0)
    assert nav._next.text().startswith("다음: ② 나")
    assert nav._previous.isHidden()
    nav._next.click()
    nav.show_step(1)
    nav._previous.click()
    assert gone == [1, 0]


def test_마지막_단계에는_다음_단추가_없다():
    nav = StepNav(STEPS)
    nav.show_step(len(STEPS) - 1)
    assert nav._next.isHidden()
    assert not nav._previous.isHidden()


def test_진행_표시는_단계_이름_밑_줄에_붙는다():
    steps = QListWidget()
    steps.addItems(STEPS)
    show_step_notes(steps, STEPS, (StepNote("대회", True), StepNote("", False), StepNote("할 차례", False)))
    assert steps.item(0).text() == "① 가\n      ✓ 대회"
    assert steps.item(1).text() == "② 나"
    assert steps.item(2).text().endswith("할 차례")
