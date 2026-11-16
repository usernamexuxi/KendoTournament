"""「?」 버튼으로 여는 도움말 창. 왼쪽 차례에서 단계를 누르면 그 절로 간다. 사용설명서를 PDF 로 내려받을 수도 있다."""

from __future__ import annotations

from collections.abc import Callable
from html import escape
from pathlib import Path

from PySide6.QtWidgets import QHBoxLayout, QListWidget, QTextBrowser, QVBoxLayout

from kendo_tournament.application.help_content import MANUAL_TITLE, SECTIONS, HelpSection, emphasized_parts
from kendo_tournament.domain.ports import ExportError
from kendo_tournament.presentation.file_dialogs import save_file
from kendo_tournament.presentation.screen_fit_dialog import ScreenFitDialog
from kendo_tournament.presentation.style import ACCENT, ACCENT_SOFT, INK, SURFACE
from kendo_tournament.presentation.widgets import button, button_row, report_error

SCREEN_SHARE = 0.85
MAX_WIDTH, MAX_HEIGHT = 1100, 860
CONTENTS_WIDTH = 150
BODY_PT = 11
CSS = f"""
body {{ color: {INK}; font-size: {BODY_PT}pt; }}
h1 {{ color: {ACCENT}; font-size: 18pt; margin-bottom: 10px; }}
h3 {{ color: {ACCENT}; font-size: 12pt; margin-top: 16px; margin-bottom: 0px; }}
li {{ margin-bottom: 7px; line-height: 160%; }}
"""


def _line_html(line: str) -> str:
    return "".join(f"<b>{escape(text)}</b>" if bold else escape(text) for text, bold in emphasized_parts(line))


def _section_html(index: int, section: HelpSection) -> str:
    """단계마다 남색 띠 제목 → 연한 파란 요약 상자 → 색 막대 소제목과 줄 목록. QTextBrowser 는 표 배경만 칠할 수 있어 표로 짓는다."""
    parts = [
        f'<a name="s{index}"></a><br>',
        f'<table width="100%" cellpadding="10" bgcolor="{ACCENT}"><tr><td>'
        f'<span style="color:{SURFACE}; font-size:15pt; font-weight:bold;">{escape(section.title)}</span></td></tr></table>',
        f'<table width="100%" cellpadding="10" bgcolor="{ACCENT_SOFT}"><tr><td>'
        f'<span style="color:{INK};">{escape(section.summary)}</span></td></tr></table>',
    ]
    for group in section.groups:
        parts.append(f'<h3><span style="color:{ACCENT};">▎</span>{escape(group.heading)}</h3><ul>')
        parts += [f"<li>{_line_html(line)}</li>" for line in group.lines]
        parts.append("</ul>")
    return "".join(parts)


def help_html() -> str:
    body = "".join(_section_html(index, section) for index, section in enumerate(SECTIONS))
    return f"<html><body><h1>{escape(MANUAL_TITLE)}</h1>{body}</body></html>"


class HelpDialog(ScreenFitDialog):
    def __init__(self, write_manual: Callable[[Path], Path], parent=None) -> None:
        """write_manual 은 main.py 가 넣어 준다(화면 계층이 파일 형식을 직접 알지 않게)."""
        super().__init__(parent)
        self._write_manual = write_manual
        self.setWindowTitle("도움말")
        screen = self.screen().availableGeometry()
        self.resize(min(MAX_WIDTH, int(screen.width() * SCREEN_SHARE)), min(MAX_HEIGHT, int(screen.height() * SCREEN_SHARE)))
        self._browser = QTextBrowser()
        self._browser.document().setDefaultStyleSheet(CSS)
        self._browser.setHtml(help_html())
        contents = QListWidget()
        contents.addItems([section.title for section in SECTIONS])
        contents.setFixedWidth(CONTENTS_WIDTH)
        contents.currentRowChanged.connect(lambda row: self._browser.scrollToAnchor(f"s{row}"))
        body = QHBoxLayout()
        body.addWidget(contents)
        body.addWidget(self._browser, 1)
        layout = QVBoxLayout(self)
        layout.addLayout(body, 1)
        download, close = button("사용설명서 내려받기 (PDF)", primary=True), button("닫기")
        download.clicked.connect(self._download)
        close.clicked.connect(self.accept)
        layout.addLayout(button_row(download, close))

    def _download(self) -> None:
        path = save_file(self, "사용설명서 저장", f"{MANUAL_TITLE}.pdf", "PDF 문서 (*.pdf)", ".pdf")
        if path is None:
            return
        try:
            self._write_manual(path)
        except (OSError, ExportError) as error:
            report_error(self, error)
