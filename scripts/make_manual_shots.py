"""사용설명서(PDF)에 넣을 단계별 화면 그림을 만든다.

실행: .venv/Scripts/python.exe scripts/make_manual_shots.py — 화면 모양을 바꾸면 다시 돌려 그림을 새로 만든다.
이름은 make_test_files.py 가 만든 지어낸 신청서(test_file/광명)만 쓴다. 설명서는 설치본과 공개 저장소에 들어가므로
실제 신청서(rm/)나 실제 대회 파일(.kendo)을 쓰지 않는다.
창 크기는 운영자 노트북과 같은 1280×752 다(배율 150% 화면 기준).
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from kendo_tournament import main as app_main
from kendo_tournament.application.help_content import STEP_PICTURES
from kendo_tournament.domain.division.presets import PresetChoice, make_rules
from kendo_tournament.domain.model import Event
from kendo_tournament.infrastructure.assets.app_fonts import register_app_fonts

ROOT = Path(__file__).resolve().parents[1]
FORMS = ROOT / "test_file" / "광명"
OUT = ROOT / "src" / "kendo_tournament" / "assets" / "manual"
TOURNAMENT_NAME = "제19회 광명시회장기 검도대회"
# 화면 아래 줄·저장 위치에 이 PC 의 사용자 폴더 이름이 찍히지 않게 보여 줄 경로만 바꾼다(파일은 임시 폴더에 쓴다).
SHOWN_PATH = Path("C:/Users/사용자/Documents/검도대진표") / f"{TOURNAMENT_NAME}.kendo"
WINDOW_SIZE = (1280, 752)
PICTURE_WIDTH = 1400


def main() -> int:
    if not FORMS.is_dir():
        print("지어낸 신청서가 없습니다. 먼저 scripts/make_test_files.py 를 돌리세요.", file=sys.stderr)
        return 1
    app = QApplication([])
    app_main.install_korean_buttons(app)
    register_app_fonts()
    app.setStyleSheet(app_main.STYLESHEET)
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as folder:
        app_main.save_dir = lambda: Path(folder)
        window = app_main.build_window()
        # build_window 는 세션을 창 안에만 둔다. 그림용 대회를 채우려고 여기서만 꺼내 쓴다.
        session = window._session
        session.new(TOURNAMENT_NAME)
        session.import_files(sorted(FORMS.iterdir()))
        tournament = session.tournament
        choice = PresetChoice(tuple(Event), categories=tournament.categories)
        session.set_rules(make_rules(choice, (), tournament.teams, tournament.participants))
        session.draw_missing()
        session.path = SHOWN_PATH
        window.resize(*WINDOW_SIZE)
        window.show()
        window._reload_all()
        for row, name in enumerate(STEP_PICTURES):
            window._steps.setCurrentRow(row)
            app.processEvents()
            picture = window.grab().scaledToWidth(PICTURE_WIDTH, Qt.TransformationMode.SmoothTransformation)
            picture.save(str(OUT / name))
            print(OUT / name)
        window.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
