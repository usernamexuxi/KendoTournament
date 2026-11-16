"""프로그램 시작점. 구체 클래스를 만들어 계층을 잇는 곳은 여기 하나뿐이다."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
from PySide6.QtWidgets import QApplication, QMessageBox

from kendo_tournament.application.output_book import CoverSources, OutputBook
from kendo_tournament.application.tournament_session import TournamentSession
from kendo_tournament.domain.ports import ExportError
from kendo_tournament.infrastructure.assets.app_fonts import register_app_fonts
from kendo_tournament.infrastructure.assets.cover_logo import CoverLogoFiles
from kendo_tournament.infrastructure.assets.cover_photos import PackagedCoverPhotos
from kendo_tournament.infrastructure.assets.photo_reader import PhotoFiles
from kendo_tournament.infrastructure.exporters.manual_pdf import write_manual
from kendo_tournament.infrastructure.exporters.pdf_exporter import PdfExporter
from kendo_tournament.infrastructure.inserts.cover_design import CoverDesignFiles
from kendo_tournament.infrastructure.inserts.document_inserter import DocumentInserter
from kendo_tournament.infrastructure.readers.registry import ACCEPTED_EXTENSIONS, reader_for
from kendo_tournament.infrastructure.storage.json_repository import JsonTournamentRepository
from kendo_tournament.presentation.main_window import MainWindow, WindowParts
from kendo_tournament.presentation.style import STYLESHEET

SAVE_FOLDER_NAME = "검도대진표"


def save_dir() -> Path:
    return Path.home() / "Documents" / SAVE_FOLDER_NAME


def build_window() -> MainWindow:
    session = TournamentSession(JsonTournamentRepository(), reader_for, save_dir())
    cover = CoverSources(CoverDesignFiles(), PhotoFiles(), CoverLogoFiles(save_dir()), PackagedCoverPhotos())
    parts = WindowParts(ACCEPTED_EXTENSIONS, OutputBook(session, DocumentInserter(), cover), PdfExporter(), write_manual)
    return MainWindow(session, parts)


def install_korean_buttons(app: QApplication) -> QTranslator:
    """Qt 기본 대화상자의 OK/Cancel 을 확인/취소로 바꾼다. 번역기는 앱이 살아 있는 동안 붙잡아 둬야 한다."""
    translator = QTranslator(app)
    translator.load(QLocale(QLocale.Language.Korean), "qtbase", "_", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath))
    app.installTranslator(translator)
    return translator


def _register_fonts() -> str | None:
    """글꼴을 못 읽어도 프로그램은 쓸 수 있게 띄우고(기본 글꼴로 보인다), 무엇이 잘못됐는지 알린다."""
    try:
        register_app_fonts()
    except ExportError as error:
        return str(error)
    return None


def main() -> int:
    app = QApplication(sys.argv)
    install_korean_buttons(app)
    font_problem = _register_fonts()
    app.setStyleSheet(STYLESHEET)
    window = build_window()
    window.show_on_screen()
    if font_problem:
        QMessageBox.warning(window, "글꼴", font_problem)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
