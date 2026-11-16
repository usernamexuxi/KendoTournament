"""종별 신청서 한 장 → 선수·팀. 파일로 받은 신청서(readers/category_form)와 화면에서 직접 적은 신청서가 같이 쓴다.

직접 작성은 문자로 신청한 사람을 신청서 모양 그대로 옮겨 적는 칸이다(운영자 지시). 문자 글을 통째로 해석하지는 않는다 —
문자 모양이 제각각이라 잘못 나뉘면 운영자가 알아채기 어렵다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from kendo_tournament.domain.division.category_label import Category, fill_missing_gender, parse_category
from kendo_tournament.domain.model import ELEMENTARY_LAST, Gender, Grade, Participant, Team

WRITTEN_SOURCE_PREFIX = "직접 작성: "
GENDER_PREFIX = {Gender.MALE: "남", Gender.FEMALE: "여"}
TEAM_POSITIONS = ("선봉", "중견", "주장", "후보")
_NAME_GAP = re.compile(r"[\s,，、·/]+")


def participant_from_category(where: str, name: str, dojang: str, category: Category, label: str = "") -> Participant:
    """종별에서 성별·학년·나이를 채운 선수. label 은 개인전 종별 글이고, 단체전 팀원은 팀 종별로 나가므로 비워 둔다."""
    return Participant(
        id=where,
        name=name,
        gender=category.gender,
        dojang=dojang,
        grade=Grade(category.grade_from),
        age=category.age_from,
        source=where.split("#")[0],
        category=label,
    )


def entry_lines(labels: tuple[str, ...]) -> tuple[str, ...]:
    """직접 작성 창의 개인전 줄. 「남초등 1~2학년」처럼 초등 학년을 묶은 종별은 학년마다 한 줄로 나눈다.

    운영자: 1학년·2학년을 따로 적어야 할 수 있다. 따로 적은 선수는 학년이 정해져 학년별 부문으로도 나눌 수 있다.
    그 밖의 종별(중·고·성인, 알아볼 수 없는 글)은 그대로 한 줄이다.
    """
    lines: list[str] = []
    for label in labels:
        category = parse_category(label)
        if category is None or category.grade_from == category.grade_to or category.grade_to > ELEMENTARY_LAST:
            lines.append(label)
            continue
        prefix = GENDER_PREFIX.get(category.gender, "")
        lines += [f"{prefix}초등 {grade}학년" for grade in range(category.grade_from, category.grade_to + 1)]
    return tuple(lines)


def split_names(text: str) -> tuple[str, ...]:
    """「홍길동, 김철수 이영희」처럼 쉼표·띄어쓰기·줄바꿈으로 나뉜 이름들."""
    return tuple(name for name in _NAME_GAP.split(text or "") if name)


@dataclass(frozen=True)
class IndividualLine:
    """개인전 종별 한 줄: 종별 글과 그 줄에 적은 이름들."""

    category: str
    names: tuple[str, ...]


@dataclass(frozen=True)
class TeamLine:
    """단체전 팀 하나: 종별 글, 팀 이름(A·B·C), (자리, 이름) 목록. 이름이 빈 자리는 넣지 않는다."""

    category: str
    team_name: str
    members: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class WrittenForm:
    dojang: str
    individuals: tuple[IndividualLine, ...]
    teams: tuple[TeamLine, ...]

    @property
    def source(self) -> str:
        """명단의 「가져온 파일」 칸. 같은 도장을 다시 적으면 이 값이 같아 예전 것을 바꾼다."""
        return f"{WRITTEN_SOURCE_PREFIX}{self.dojang}"


@dataclass(frozen=True)
class WrittenRoster:
    participants: tuple[Participant, ...]
    teams: tuple[Team, ...]
    problems: tuple[str, ...]


def written_roster(form: WrittenForm) -> WrittenRoster:
    """적은 신청서를 선수·팀으로. 도장이 비었거나 종별을 알아볼 수 없으면 problems 에 적고 그 줄은 넣지 않는다."""
    if not form.dojang.strip():
        return WrittenRoster((), (), ("도장(단체명)을 적어 주세요.",))
    people: list[Participant] = []
    problems: list[str] = []
    labels = [line.category for line in form.individuals]
    parsed = [parse_category(label) for label in labels]
    filled = iter(fill_missing_gender([category for category in parsed if category is not None]))
    for line, category in zip(form.individuals, parsed, strict=True):
        if category is None:
            if line.names:
                problems.append(f"종별 「{line.category}」 을 알아볼 수 없어 {len(line.names)}명을 넣지 못했습니다.")
            continue
        category = next(filled)
        for index, name in enumerate(line.names, start=1):
            where = f"{form.source}#개인-{line.category}-{index}"
            people.append(participant_from_category(where, name, form.dojang, category, line.category))
    teams = []
    for number, line in enumerate(form.teams):
        team, members, problem = _team(form, number, line)
        if problem:
            problems.append(problem)
        if team is not None:
            teams.append(team)
            people += members
    return WrittenRoster(tuple(people), tuple(teams), tuple(problems))


def _team(form: WrittenForm, number: int, line: TeamLine) -> tuple[Team | None, list[Participant], str]:
    filled = [(position, name.strip()) for position, name in line.members if name.strip()]
    if not filled:
        return None, [], ""
    category = parse_category(line.category)
    if category is None:
        return None, [], f"단체전 종별 「{line.category}」 을 알아볼 수 없어 {line.team_name}팀을 넣지 못했습니다."
    team_name = line.team_name.strip().removesuffix("팀")
    members = [
        participant_from_category(f"{form.source}#단체-{number}-{team_name}-{index}", name, form.dojang, category)
        for index, (_, name) in enumerate(filled, start=1)
    ]
    team = Team(
        f"{form.source}#팀{number}-{form.dojang}-{team_name}",
        f"{form.dojang} {team_name}",
        form.dojang,
        tuple(member.id for member in members),
        line.category,
        tuple(position for position, _ in filled),
    )
    return team, members, ""
