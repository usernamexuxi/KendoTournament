"""화면 색·간격·글자 크기 토큰과 스타일시트. 모양을 바꾸려면 이 파일만 고친다.

쓰는 분이 나이가 있는 운영자라(개발자 지시) 글자를 크게, 대비를 높게, 누를 곳을 넓게 잡았다.
색은 파란색과 흰색 두 가지를 중심으로 쓴다.
"""

from __future__ import annotations

INK = "#14213d"
MUTED = "#4a5a70"
LINE = "#c9d6e8"
SURFACE = "#ffffff"
CANVAS = "#f2f6fc"
ACCENT = "#1652a8"
ACCENT_DARK = "#0f3d80"
ACCENT_SOFT = "#e3edfb"
WARN = "#8a3b00"
WARN_SOFT = "#fff1dc"
SELECTED = "#ffe08a"
PICKED_ROW = "#cfe2fb"
SCROLL_HANDLE = "#8fa7c8"
SPACING = 14
# 기본 스크롤 막대는 운영자가 잡기 어렵다고 해서(개발자 지시) 손가락 굵기에 가깝게 넓혔다.
SCROLLBAR_PX = 22
# 화면 글꼴은 운영자가 보기 편하다고 한 맑은 고딕, 인쇄 미리보기는 만드는 PDF 와 같은 Pretendard(배포본에 넣은 글꼴, main.py 가 등록).
FONT_FAMILY = "맑은 고딕"
PRINT_FONT_FAMILY = "Pretendard"
PRINT_TITLE_FONT_FAMILY = "ChungjuKimSaeng TTF"
BASE_PT = 12
TITLE_PT = 19
STEP_PT = 14

STYLESHEET = f"""
* {{ font-family: '{FONT_FAMILY}'; font-size: {BASE_PT}pt; color: {INK}; }}
QMainWindow, QWidget#page {{ background: {CANVAS}; }}
QWidget#sidebar {{ background: {ACCENT}; }}
QFileDialog QWidget#sidebar {{ background: {SURFACE}; border: 1px solid {LINE}; }}
QFileDialog QAbstractItemView::item:hover {{ background: {CANVAS}; }}
QFileDialog QAbstractItemView::item:selected,
QFileDialog QAbstractItemView::item:selected:!active {{ background: {PICKED_ROW}; color: {INK}; }}
QLabel#appTitle {{ color: white; font-size: {STEP_PT + 2}pt; font-weight: bold; padding: 22px 18px 18px 18px; }}
QListWidget#steps {{ background: {ACCENT}; border: none; outline: 0; }}
QListWidget#steps::item {{ color: white; font-size: {STEP_PT}pt; padding: 16px 18px; border-left: 5px solid transparent; }}
QListWidget#steps::item:hover {{ background: {ACCENT_DARK}; }}
QListWidget#steps::item:selected {{ background: {SURFACE}; color: {ACCENT}; font-weight: bold; border-left: 5px solid {ACCENT_DARK}; }}
QLabel#pageTitle {{ font-size: {TITLE_PT}pt; font-weight: bold; color: {ACCENT_DARK}; }}
QLabel#hint {{ color: {MUTED}; line-height: 150%; }}
QLabel#warning {{ color: {WARN}; background: {WARN_SOFT}; border: 1px solid #f1c48a; border-radius: 6px; padding: 10px 14px; }}
QGroupBox {{ background: {SURFACE}; border: 1px solid {LINE}; border-radius: 8px; margin-top: 18px; padding: 16px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; color: {ACCENT}; font-weight: bold; }}
QPushButton {{ background: {SURFACE}; color: {ACCENT}; border: 2px solid {ACCENT}; border-radius: 6px;
    padding: 9px 20px; min-height: 28px; font-weight: bold; }}
QPushButton:hover {{ background: {ACCENT_SOFT}; }}
QPushButton#primary {{ background: {ACCENT}; color: white; }}
QPushButton#primary:hover {{ background: {ACCENT_DARK}; border-color: {ACCENT_DARK}; }}
QPushButton#help {{ border-radius: 22px; min-width: 44px; max-width: 44px; min-height: 44px; max-height: 44px;
    padding: 0; font-size: {STEP_PT + 4}pt; background: {SURFACE}; color: {ACCENT}; border: 2px solid {ACCENT}; }}
QTableWidget, QListWidget, QTextBrowser {{ background: {SURFACE}; border: 1px solid {LINE}; border-radius: 6px;
    gridline-color: {LINE}; selection-background-color: {ACCENT_SOFT}; selection-color: {INK}; }}
QListWidget::item {{ padding: 8px 6px; }}
QTableWidget::item {{ padding: 6px; }}
QHeaderView::section {{ background: {ACCENT_SOFT}; color: {ACCENT_DARK}; font-weight: bold; border: none;
    border-bottom: 1px solid {LINE}; padding: 8px; }}
QLineEdit, QComboBox, QSpinBox, QDateEdit {{ background: {SURFACE}; border: 1px solid {LINE}; border-radius: 6px;
    padding: 6px 10px; min-height: 26px; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDateEdit:focus {{ border: 2px solid {ACCENT}; }}
QCheckBox, QRadioButton {{ spacing: 8px; padding: 4px 10px 4px 0; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 22px; height: 22px; }}
QStatusBar {{ background: {SURFACE}; border-top: 1px solid {LINE}; color: {MUTED}; font-size: {BASE_PT - 2}pt; }}
QMessageBox QLabel {{ font-size: {BASE_PT + 1}pt; }}
QComboBox:disabled {{ color: {LINE}; background: {CANVAS}; border-color: {CANVAS}; }}
QTableWidget QComboBox {{ margin: 6px 4px; padding: 4px 8px; }}
QTableWidget QPushButton {{ margin: 6px 6px; padding: 0 14px; min-height: 34px; font-size: {BASE_PT - 1}pt; }}
QListWidget#printList::item {{ padding: 3px 6px; }}
QListWidget#divisionResult {{ font-size: {BASE_PT + 1}pt; }}
QLabel#sectionTitle {{ color: {ACCENT_DARK}; font-size: {BASE_PT + 2}pt; font-weight: bold;
    border-left: 5px solid {ACCENT}; padding: 2px 0 2px 10px; margin-top: 18px; }}
QFrame#card {{ background: {SURFACE}; border: 1px solid {LINE}; border-radius: 10px; padding: 14px; }}
QFrame#card QLabel {{ background: transparent; border: none; }}
QLabel#cardTitleNext {{ color: {ACCENT_DARK}; font-size: {BASE_PT + 3}pt; font-weight: bold; padding-top: 14px; }}
QLabel#cardTitle {{ color: {ACCENT_DARK}; font-size: {BASE_PT + 3}pt; font-weight: bold; padding-bottom: 6px;
    border: none; border-bottom: 3px solid {ACCENT}; }}
QLabel#logoSlot {{ border: 2px dashed {LINE}; border-radius: 6px; background: {SURFACE}; color: {MUTED}; }}
QToolButton#coverTile {{ background: {SURFACE}; border: 3px solid transparent; border-radius: 8px; padding: 4px;
    font-size: {BASE_PT - 1}pt; color: {INK}; }}
QToolButton#coverTile:hover {{ background: {ACCENT_SOFT}; }}
QToolButton#coverTile:checked {{ border-color: {ACCENT}; background: {ACCENT_SOFT}; font-weight: bold; }}
QListWidget#divisionResult::item {{ padding: 12px 10px; border-bottom: 1px solid {LINE}; }}
QScrollBar:vertical {{ background: {CANVAS}; width: {SCROLLBAR_PX}px; margin: 0; border: none; }}
QScrollBar:horizontal {{ background: {CANVAS}; height: {SCROLLBAR_PX}px; margin: 0; border: none; }}
QScrollBar::handle:vertical {{ background: {SCROLL_HANDLE}; border-radius: {SCROLLBAR_PX // 2 - 3}px;
    min-height: 48px; margin: 3px; }}
QScrollBar::handle:horizontal {{ background: {SCROLL_HANDLE}; border-radius: {SCROLLBAR_PX // 2 - 3}px;
    min-width: 48px; margin: 3px; }}
QScrollBar::handle:hover, QScrollBar::handle:pressed {{ background: {ACCENT}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; border: none; background: none; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
"""


def swatch_style(color: str, chosen: bool) -> str:
    """표지 색 고르기 단추. 색 자체가 고를 값이라 단추마다 바탕색이 다르다. 고른 색은 굵은 테두리."""
    border = f"4px solid {INK}" if chosen else f"2px solid {LINE}"
    return (
        f"QPushButton {{ background: {color}; border: {border}; border-radius: 22px; "
        "min-width: 44px; max-width: 44px; min-height: 44px; max-height: 44px; padding: 0; }}"
    )
