"""만드는 파일(PDF)과 그 인쇄 미리보기에 쓸 한글 글꼴. 배포본에 Pretendard 를 넣어 어느 PC 에서나 같은 모양으로 나오게 한다.

운영자가 만드는 파일의 글꼴은 맑은 고딕보다 깔끔한 것을 원했다(프로그램 화면은 맑은 고딕 그대로). Pretendard 는 SIL OFL 1.1 이라 함께 배포해도 되고,
그 조건으로 라이선스 글(Pretendard-OFL.txt)을 같은 폴더에 둔다.
표지 제목은 참고 카탈로그와 같은 충주김생체(충주시 무료 배포, 상업 이용·프로그램 탑재 허용, 판매·변형 금지)를 쓴다.
"""

from __future__ import annotations

from pathlib import Path

from kendo_tournament.domain.ports import ExportError

FONT_DIR = Path(__file__).resolve().parents[2] / "assets" / "fonts"
REGULAR_FILE = FONT_DIR / "Pretendard-Regular.ttf"
BOLD_FILE = FONT_DIR / "Pretendard-Bold.ttf"
TITLE_FILE = FONT_DIR / "ChungjuKimSaeng.ttf"


class FontMissing(ExportError):
    pass


def require_fonts() -> tuple[Path, Path, Path]:
    """(보통, 굵게, 표지 제목) 글꼴 파일. 하나라도 없으면 FontMissing."""
    for path in (REGULAR_FILE, BOLD_FILE, TITLE_FILE):
        if not path.exists():
            raise FontMissing(f"글꼴 파일을 찾을 수 없습니다: {path}. 프로그램을 다시 설치해 주세요.")
    return REGULAR_FILE, BOLD_FILE, TITLE_FILE
