"""Qt 에 배포본의 글꼴(Pretendard · 표지 제목 글꼴)을 등록한다(인쇄 미리보기가 PDF 와 같은 글꼴로 보이게)."""

from __future__ import annotations

from PySide6.QtGui import QFontDatabase

from kendo_tournament.domain.ports import ExportError
from kendo_tournament.infrastructure.exporters.fonts import require_fonts


def register_app_fonts() -> None:
    """보통·굵게·표지 제목 글꼴을 등록한다. 파일이 없거나 깨졌으면 ExportError."""
    for path in require_fonts():
        if QFontDatabase.addApplicationFont(str(path)) < 0:
            raise ExportError(f"글꼴 파일을 읽을 수 없습니다: {path.name}. 프로그램을 다시 설치해 주세요.")
