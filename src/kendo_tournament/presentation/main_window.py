"""메인 창: 왼쪽에 단계 목록, 오른쪽에 그 단계 화면, 오른쪽 위에 「?」 도움말."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QMainWindow, QStackedWidget, QVBoxLayout, QWidget

from kendo_tournament.application.output_book import OutputBook
from kendo_tournament.application.step_progress import saved_text, step_notes
from kendo_tournament.application.tournament_session import TournamentSession
from kendo_tournament.domain.ports import BracketExporter
from kendo_tournament.presentation.bracket_view import BracketView
from kendo_tournament.presentation.division_view import DivisionView
from kendo_tournament.presentation.help_dialog import HelpDialog
from kendo_tournament.presentation.output_view import OutputView
from kendo_tournament.presentation.review_view import ReviewView
from kendo_tournament.presentation.roster_view import RosterView
from kendo_tournament.presentation.step_notes import show_step_notes
from kendo_tournament.presentation.tournament_view import TournamentView
from kendo_tournament.presentation.widgets import button

APP_TITLE = "검도 대진표"
STEPS = ("① 대회 정보", "② 선수 명단", "③ 종별 나누기", "④ 대진 짜기", "⑤ 인쇄 순서", "⑥ 책자 만들기")
REVIEW_STEP = 4
SIDEBAR_WIDTH = 210
PREFERRED_WIDTH, PREFERRED_HEIGHT = 1280, 820
# 진행 표시·저장 알림은 어느 화면에서 무엇을 바꿔도 맞아야 해서, 화면마다 신호를 잇는 대신 짧은 간격으로 다시 읽는다.
STATUS_INTERVAL_MS = 1000


@dataclass(frozen=True)
class WindowParts:
    """main.py 가 만들어 넘기는 부품들."""

    accepted_extensions: tuple[str, ...]
    book: OutputBook
    pdf_exporter: BracketExporter
    write_manual: Callable[[Path], Path]


class MainWindow(QMainWindow):
    def __init__(self, session: TournamentSession, parts: WindowParts) -> None:
        super().__init__()
        self._session = session
        self._write_manual = parts.write_manual
        self.resize(PREFERRED_WIDTH, PREFERRED_HEIGHT)

        self._tournament = TournamentView(session)
        self._roster = RosterView(session, parts.accepted_extensions)
        self._division = DivisionView(session, parts.accepted_extensions)
        self._bracket = BracketView(session)
        self._review = ReviewView(session)
        self._output = OutputView(parts.book, parts.pdf_exporter, session.default_path().parent)
        pages = (self._tournament, self._roster, self._division, self._bracket, self._review, self._output)

        self._stack = QStackedWidget()
        for page in pages:
            self._stack.addWidget(page)
        self._steps = QListWidget()
        self._steps.setObjectName("steps")
        self._steps.addItems(STEPS)
        self._steps.currentRowChanged.connect(self._go_to)
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(SIDEBAR_WIDTH)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        app_title = QLabel(APP_TITLE)
        app_title.setObjectName("appTitle")
        sidebar_layout.addWidget(app_title)
        sidebar_layout.addWidget(self._steps, 1)

        header = QHBoxLayout()
        help_button = button("?")
        help_button.setObjectName("help")
        help_button.setToolTip("도움말과 사용설명서")
        help_button.clicked.connect(lambda: HelpDialog(self._write_manual, self).exec())
        header.addStretch(1)
        header.addWidget(help_button)

        right = QVBoxLayout()
        right.setContentsMargins(0, 8, 12, 0)
        right.addLayout(header)
        right.addWidget(self._stack, 1)
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.addWidget(sidebar)
        body.addLayout(right, 1)
        central = QWidget()
        central.setLayout(body)
        self.setCentralWidget(central)

        self._tournament.tournament_replaced.connect(self._reload_all)
        self._roster.roster_changed.connect(self._roster_changed)
        self._division.divisions_changed.connect(self._bracket.refresh)
        self._bracket.go_export.connect(lambda: self._steps.setCurrentRow(REVIEW_STEP))
        self._steps.setCurrentRow(0)
        self._update_title()
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._show_status)
        self._status_timer.start(STATUS_INTERVAL_MS)
        self._show_status()

    def show_on_screen(self) -> None:
        """보통 크기로 띄우되, 화면(작업 표시줄 뺀 곳)보다 크면 최대화한다.

        노트북 배율(150%)에서는 보통 크기가 화면보다 커서 창 아래가 작업 표시줄 밑으로 숨었다.
        """
        self.show()
        if not self.screen().availableGeometry().contains(self.frameGeometry()):
            self.showMaximized()

    def _go_to(self, row: int) -> None:
        self._stack.setCurrentIndex(row)
        page = self._stack.currentWidget()
        refresh = getattr(page, "refresh", None)
        if refresh:
            refresh()
        self._update_title()

    def _roster_changed(self) -> None:
        """명단이 바뀌면 부문 인원도 바뀌므로 규칙이 있으면 부문을 다시 나눈다(대진은 지킨다)."""
        if self._session.tournament.rules:
            self._session.refresh_divisions()

    def _reload_all(self) -> None:
        for index in range(self._stack.count()):
            refresh = getattr(self._stack.widget(index), "refresh", None)
            if refresh:
                refresh()
        self._update_title()
        self._show_status()

    def _update_title(self) -> None:
        saved = self._session.path.name if self._session.path else "저장 전"
        self.setWindowTitle(f"{APP_TITLE} — {self._session.tournament.name} ({saved})")

    def _show_status(self) -> None:
        session = self._session
        show_step_notes(self._steps, STEPS, step_notes(session.tournament))
        file_name = (session.path or session.default_path()).name
        self.statusBar().showMessage(saved_text(session.saved_at, file_name, opened=session.path is not None))
