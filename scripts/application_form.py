"""실제 광명시 회장기 신청서 양식을 그대로 본뜬 쪽(문단과 표)을 만든다. make_test_files.py 가 쓴다.

양식(사용자가 준 실제 신청서, rm/ — 시험 자료에 넣지 않는다):
- 단체전 쪽: 제목 · 「참가신청서(단체전)」 · 단체명/주소/대표자/전화번호 표 · ○표 안내 ·
  「팀별 | 종별」 표 · 「A팀 | 성 명 | 생년 월일 | B팀 …」 표(선봉·중견·주장·후보) · 신청 문구·서명.
  종별마다 한 쪽이다. 팀을 안 낸 도장은 종별을 고르지 않은 빈 쪽을 그대로 낸다(실제로 그렇게 온다).
- 개인전 쪽: 「종 별 | 성 명 × 6」 표, 종별마다 두 줄이고 이름이 넘치면 줄이 늘어난다.
"""

from __future__ import annotations

from dataclasses import dataclass

INDIVIDUAL_CATEGORIES = (
    "남초등 1~2학년", "남초등 3~4학년", "남초등 5~6학년", "여초등 1~3학년", "여초등 4~6학년",
    "여청소년 (중,고)", "중등부", "고등부", "남자청년부 20~35세", "남자장년부 36~47세", "남자중년부 48세부터",
    "여자일반부",
)  # fmt: skip
TEAM_CATEGORIES = ("초등저학년 1~3학년", "초등고학년 4~6학년", "여청소년부(중,고)", "남청소년부(중,고)", "남자일반부")
POSITIONS = ("선봉", "중견", "주장", "후보")
TEAM_LETTERS = "ABC"
NAMES_PER_ROW = 6
ROWS_PER_CATEGORY = 2
# 실제 양식은 고르지 않은 종별을 띄어 쓴 채 한 칸에 늘어놓는다.
UNCHOSEN_SEPARATOR = "     "
TEAM_NOTES = ("※ 해당란에 ○표 하세요.(참가 팀수 제한은 없습니다.)", "※ 단체전 남, 여 혼성 (3인조)")
INDIVIDUAL_NOTE = "※ 참가선수 인원수 제한은 없습니다."

Rows = tuple[tuple[str, ...], ...]
Block = str | Rows
Page = tuple[Block, ...]


@dataclass(frozen=True)
class TeamMember:
    name: str
    birth: str


@dataclass(frozen=True)
class Applicant:
    """도장 하나의 신청 내용. teams 는 단체전 종별 → 팀(자리 순서대로 선수, 후보 없으면 3명) 목록."""

    dojang: str
    address: str
    head: str
    phone: str
    individuals: dict[str, list[str]]
    teams: dict[str, list[list[TeamMember]]]


@dataclass(frozen=True)
class Contest:
    title: str
    signed_on: str
    recipient: str


def _info(applicant: Applicant) -> Rows:
    return (
        ("단 체 명", applicant.dojang, "주    소", applicant.address),
        ("대 표 자", applicant.head, "전화번호", applicant.phone),
    )


def _closing(contest: Contest, applicant: Applicant) -> tuple[str, ...]:
    return (
        f"위와 같이 {contest.title}에 참가신청 합니다.",
        contest.signed_on,
        f"대표자 :  {applicant.head} (직인)",
        f"{contest.recipient}  귀하",
    )


def _team_table(teams: list[list[TeamMember]]) -> Rows:
    count = max(len(teams), len(TEAM_LETTERS))
    head = tuple(cell for letter in TEAM_LETTERS[:count] for cell in (f"{letter}팀", "성   명", "생년 월일"))
    rows = [head]
    for position_no, position in enumerate(POSITIONS):
        row: list[str] = []
        for team_no in range(count):
            members = teams[team_no] if team_no < len(teams) else []
            member = members[position_no] if position_no < len(members) else None
            row += [position, member.name if member else "", member.birth if member else ""]
        rows.append(tuple(row))
    return tuple(rows)


def _team_page(contest: Contest, applicant: Applicant, category: str | None) -> Page:
    chosen = category or UNCHOSEN_SEPARATOR.join(TEAM_CATEGORIES)
    teams = applicant.teams.get(category, []) if category else []
    return (
        contest.title,
        "참가신청서(단체전)",
        _info(applicant),
        *TEAM_NOTES,
        (("팀별", chosen),),
        _team_table(teams),
        *_closing(contest, applicant),
    )


def _category_rows(category: str, names: list[str]) -> list[tuple[str, ...]]:
    row_count = max(ROWS_PER_CATEGORY, -(-len(names) // NAMES_PER_ROW))
    rows = []
    for row_no in range(row_count):
        chunk = names[row_no * NAMES_PER_ROW : (row_no + 1) * NAMES_PER_ROW]
        label = category if row_no == 0 else ""
        rows.append((label, *chunk, *([""] * (NAMES_PER_ROW - len(chunk)))))
    return rows


def _individual_page(contest: Contest, applicant: Applicant) -> Page:
    grid = [("종 별", *(["성   명"] * NAMES_PER_ROW))]
    for category in INDIVIDUAL_CATEGORIES:
        grid += _category_rows(category, applicant.individuals.get(category, []))
    return (
        contest.title,
        "참가신청서 (개인전)",
        _info(applicant),
        INDIVIDUAL_NOTE,
        tuple(grid),
        *_closing(contest, applicant),
    )


def form_pages(contest: Contest, applicant: Applicant) -> list[Page]:
    """단체전 쪽(종별마다, 팀이 없으면 빈 쪽 하나) 다음에 개인전 쪽."""
    chosen = [category for category in TEAM_CATEGORIES if applicant.teams.get(category)]
    pages = [_team_page(contest, applicant, category) for category in chosen] or [_team_page(contest, applicant, None)]
    return [*pages, _individual_page(contest, applicant)]
