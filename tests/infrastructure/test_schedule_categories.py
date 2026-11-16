"""경기일정 문서(신청서 양식 없음)의 「경기장배치」 표에서 종별을 읽는다. 칸 글은 실제 경기일정 모양을 본떴다."""

from kendo_tournament.infrastructure.readers.document_text import Paragraph, Table, blocks_to_result

COURTS = (
    ("제1경기장", "제2경기장"),
    (
        "남초등부 1학년부 개인전 남초등부1~2학년 단체전 여자청소년부개인전(중.고)",
        "여초등부 1~3학년부 개인전 남자일반부 단체전A",
    ),
    ("점심시간 없음", "점심시간 없음"),
    ("남자 중등부 개인전 남자일반부 단체전B", "여자일반부 개인전"),
)


def test_경기일정의_경기장배치_표에서_개인전_단체전_종별을_읽는다():
    result = blocks_to_result([Paragraph("경기일정"), Table(COURTS)], "경기일정.hwp")
    table = result.form_categories
    assert table is not None
    assert table.individual == ("남초등부 1학년부", "여자청소년부(중.고)", "여초등부 1~3학년부", "남자 중등부", "여자일반부")
    assert table.team == ("남초등부1~2학년", "남자일반부")


def test_신청서_양식이_있으면_경기장배치보다_양식의_종별이_먼저다():
    form = (("종 별", "성   명"), ("남초등 1~2학년", ""))
    result = blocks_to_result([Table(COURTS), Table(form)], "요강.hwp")
    assert result.form_categories.individual == ("남초등 1~2학년",)
