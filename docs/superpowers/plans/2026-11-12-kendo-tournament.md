# 검도 대진표 프로그램 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 신청 문서에서 명단을 읽어 부문을 나누고 같은 도장을 분리한 토너먼트 대진표를 A4 PDF·hwpx 로 출력하는 오프라인 윈도우 프로그램.

**Architecture:** 계층형이다. presentation(PySide6) → application(유스케이스) → domain(순수 파이썬) 으로 의존한다. infrastructure 는 `domain/ports.py` 의 Protocol 을 구현하고, 조립은 `main.py` 에서만 한다.

**Tech Stack:** Python 3.13, PySide6, python-docx, pdfplumber, olefile, reportlab, PyInstaller(onedir → zip), pytest.

**Spec:** `docs/superpowers/specs/2026-11-12-kendo-tournament-design.md`

## Global Constraints

- domain 은 표준 라이브러리만 import 한다.
- 용지는 항상 A4 다.
- PDF 글꼴은 `C:\Windows\Fonts\malgun.ttf` 를 쓰고 배포본에 넣지 않는다(승인됨).
- 허용 확장자는 `.docx .hwp .hwpx .pdf` 뿐이다. `.doc` 는 「워드에서 .docx 로 다시 저장해 주세요」라고 안내하고 거부한다.
- 연 나이와 구분의 대응: 8~13 = 초1~6, 14~16 = 중1~3, 17~19 = 고1~3, 20 이상 = 성인, 8 미만 = 확인 필요.
- 적힌 학년은 보정하지 않는다.
- 부문 합치기는 같은 종목·같은 성별 안에서 바로 이웃한 구분 범위와만 한다. 그래도 모자라면 다시 합친다.
- 경기 번호 기본값은 라운드마다 「왼쪽 위→아래, 다음 오른쪽 위→아래」다. 개발자가 예시를 보내기로 했으므로 `NumberingStyle` 로 바꿀 수 있게 한다.
- 시험 자료는 가짜 이름만 쓴다. 로그에 선수 이름을 남기지 않는다. git 은 로컬만 쓴다.

## Review Focus

1. 한 도장이 절반을 넘는 부문: 분리할 수 없는 1회전 대결만 남고, `round1_conflicts` 로 보고되어야 한다 → Task 2 시험.
2. 기권을 빼서 한 1회전 묶음이 통째로 비는 경우: 그 경기는 번호 없는 부전승이 되고, 상대는 다음 라운드로 그냥 올라가야 한다 → Task 3 시험.
3. 참가자 1명 또는 2명인 부문: 1명이면 「단독 출전」, 2명이면 결승 한 경기다 → Task 2·3 시험.
4. 머리글이 「성 명」처럼 띄어 쓰였거나 도장명이 표 밖 문단에만 있는 워드 문서: 그래도 읽혀야 한다 → Task 5 시험.
5. 64강을 넘는 대진: A4 여러 장으로 나뉘고, 글자가 최소 크기 아래로 내려가지 않아야 한다 → Task 4 시험.

---

### Task 1: 프로젝트 골격 + 모델 + 구분 산출 + 부문 규칙

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `src/kendo_tournament/__init__.py`
- Create: `src/kendo_tournament/domain/model.py`
- Create: `src/kendo_tournament/domain/division/grade.py`, `dojang.py`, `builder.py`
- Test: `tests/domain/test_grade.py`, `test_dojang.py`, `test_division_builder.py`

**Interfaces (Produces):**
- `Gender(Enum) MALE/FEMALE` · `Event(Enum) INDIVIDUAL/TEAM`
- `Grade` 는 1~13 의 정수 래퍼다. 1~6=초, 7~9=중, 10~12=고, 13=성인이고 `.label` 이 있다.
- `Participant(id, name, gender, dojang, grade: Grade|None, age: int|None, region, source)`
- `Team(id, name, dojang, member_ids: tuple[str,...])`
- `Entry(id, name, dojang)` — 대진 칸에 들어가는 것(선수 또는 팀)
- `DivisionRule(id, event, gender: Gender|None, grade_from, grade_to, team_size: int|None, min_entries: int|None, merge_direction: MergeDirection|None)`
- `Division(rule_ids: tuple, label, event, entries: tuple[Entry,...])`
- `parse_grade(text) -> Grade|None` · `grade_from_age(age) -> Grade|None` · `resolve_grade(p) -> Grade|None`
- `dojang_key(name) -> str`
- `build_divisions(participants, teams, rules) -> DivisionResult(divisions, unassigned, multi_assigned, merges)`

- [ ] 시험 작성: 나이 경계 7→None, 8→초1, 13→초6, 14→중1, 16→중3, 17→고1, 19→고3, 20→성인. 「초3」「초등 3」「중1」「고 2」「성인」을 인식하고, 「3학년」은 None 이다. 공백과 앞뒤 공백을 뺀 도장 키가 같은지 확인한다. 부문을 나누고, 연속으로 합치고, 후보가 없을 때 멈추고, 혼성 규칙이 성별을 가리지 않는지 확인한다.
- [ ] 구현 → 시험 통과 → 커밋

### Task 2: 대진 생성 (부전승 · 같은 도장 분리 · 검증)

**Files:** `src/kendo_tournament/domain/draw/bracket.py`, `draw.py`, `validate.py` · Test `tests/domain/test_draw.py`

**Interfaces:**
- `Bracket(division_label, size, slots: list[Entry|None], seed: int)`
- `bracket_size(n) -> int`
- `draw_bracket(entries, rng: random.Random, seed) -> Bracket`
- `first_meeting_round(size, i, j) -> int`
- `round1_conflicts(bracket) -> list[tuple[int,int]]`

**알고리즘:**
- 1회전 묶음(P/2개)을 비트 반전 순서로 늘어놓는다. 앞의 (P−N)개 묶음이 부전승 묶음이다.
- 선수를 도장 인원 내림차순(동률이면 무작위)으로, 도장 안에서는 섞어서 줄 세운다.
- 1차로 모든 묶음의 첫 칸을 채우고, 2차로 부전승이 아닌 묶음의 둘째 칸을 같은 순서로 채운다.
- 마지막으로 각 노드의 좌우를 무작위로 뒤집는다. 뒤집어도 만나는 라운드는 변하지 않는다.

- [ ] 시험: N=1~64, 도장 구성 300가지 무작위. 칸 수 = P, 부전승끼리 맞붙지 않는다. 가장 큰 도장 ≤ P/2 이면 1회전 충돌이 없다. 같은 seed 면 같은 결과다.
- [ ] 구현 → 통과 → 커밋

### Task 3: 경기 번호 · 대진 수정

> **2026-11-12 개정 (개발자 예시 반영, spec 6.3):** 아래 `NumberingStyle` 대신 블록 번호 방식을 쓴다.
> - `number_matches(bracket, block_size, third_place) -> list[Match]`
> - `Match(round, index, label)` 이고 `label` 은 블록 안 번호 `"1"…` 또는 `"준결승"`·`"결승"`·`"8강"`·`"3위 결정전"` 이다.
> - 블록 안에서는 라운드마다 위에서 아래로 매긴다.
> - `default_block_size(P)` 는 P≥32 이면 16, 아니면 P/2 다.
> - 선수 번호는 칸 번호 + 1 이다(왼쪽 절반 → 오른쪽 절반).
> - 시험: 64강에서 블록이 4개이고, 블록마다 1~15 가 빠짐없이 있으며, 준결승 2개와 결승 1개가 있다.

**Files:** `domain/draw/numbering.py`, `domain/draw/editing.py` · Test `tests/domain/test_numbering.py`, `test_editing.py`

**Interfaces:**
- `NumberingStyle(Enum) ROUND_BY_ROUND / SIDE_BY_SIDE`
- `Match(number, round, index, side)`
- `number_matches(bracket, style, third_place: bool) -> list[Match]`
  - 양쪽 하위 트리에 모두 선수가 있는 경기만 번호를 받는다.
  - 3위 결정전은 없다(2026-11-12 개발자 지시, 늘 공동 3위).
- `swap_slots(b, i, j) -> Bracket` · `withdraw(b, i) -> Bracket` · `insert_entry(b, i, entry) -> Bracket`
  - 빈 칸이 아니면 `ValueError` 를 던진다.
- `recommend_insert_slots(b, dojang) -> list[int]` — 같은 도장과 늦게 만나는 칸부터 늘어놓는다.

- [ ] 시험: 8강 ROUND_BY_ROUND → 1회전 왼쪽 1·2, 오른쪽 3·4, 2회전 5·6, 결승 7. SIDE_BY_SIDE → 1·2·3 / 4·5·6 / 7. 부전승이 낀 1회전에는 번호가 없다. 묶음이 통째로 빈 경우, 기권을 뺀 뒤 나머지 칸이 그대로인지도 확인한다.
- [ ] 구현 → 통과 → 커밋

### Task 4: 대진표 좌표 계산 (layout)

**Files:** `domain/layout/bracket_layout.py` · Test `tests/domain/test_layout.py`

**Interfaces:**
- `PageLayout(width_mm=210, height_mm=297, texts: list[TextItem], lines: list[LineItem])`
- `TextItem(x, y, text, size_pt, align)` · `LineItem(x1, y1, x2, y2)`
- `layout_bracket(bracket, matches, header: SheetHeader) -> list[PageLayout]`
- `SheetHeader(title, date_text, division_label)`

**배치 규칙:**
- 64칸 이하는 한 장에 그린다. 왼쪽 절반은 왼쪽에서 오른쪽으로, 오른쪽 절반은 거울상으로 그리고, 결승은 가운데에 둔다.
- 그보다 크면 절반씩 한 장에 한쪽 방향으로 그리고 「이어짐」을 표시한다.
- 최소 글자 크기는 7pt 다.

- [ ] 시험: 8강은 1쪽이고 모든 좌표가 용지 안에 있다. 128강은 여러 쪽이고 글자 크기는 7pt 이상이다.
- [ ] 구현 → 통과 → 커밋

### Task 5: 워드 리더 + PDF 출력 + 유스케이스 (처음부터 끝까지)

**Files:**
- `domain/ports.py`
- `infrastructure/readers/{registry,table_rows,docx_reader}.py`
- `infrastructure/exporters/pdf_exporter.py`
- `application/{import_roster,draw_brackets,export_brackets}.py`

**Test:** `tests/infrastructure/test_docx_reader.py`, `tests/application/test_end_to_end.py`. 시험용 docx 는 python-docx 로 시험 안에서 만든다.

**Interfaces:**
- `RosterReader.read(path) -> ReadResult(participants, teams, problems: list[str])`
- `reader_for(path) -> RosterReader` — 허용 목록에 없으면 `UnsupportedFormat(message)`
- `rows_to_participants(header, rows, context_dojang, source)` — 머리글 동의어 상수는 `table_rows.py` 한 곳에만 둔다.
- `BracketExporter.export(pages, path)`

- [ ] 시험:
  - 「성 명」 머리글을 인식한다.
  - 표 위 문단의 「도장명: ○○검도관」을 쓴다.
  - 성별이 빠진 행은 problems 에 들어간다.
  - 워드 3장 → 부문 → 대진 → PDF 파일이 생기고 첫 바이트가 `%PDF` 다.
- [ ] 구현 → 통과 → 커밋

### Task 6: 저장소 + 화면

**Files:**
- `infrastructure/storage/json_repository.py`
- `application/tournament_service.py`
- `presentation/{main_window,roster_view,division_view,bracket_view}.py`
- `main.py`

**Test:** `tests/infrastructure/test_json_repository.py`(저장 → 불러오기 왕복), `tests/presentation/test_smoke.py`(offscreen 으로 창 생성)

- [ ] 구현 → 시험 → 실제로 띄워 화면 확인 → 커밋

### Task 7: hwpx 출력

**Files:** `infrastructure/exporters/hwpx_exporter.py` · Test `tests/infrastructure/test_hwpx_exporter.py`

- 글자는 글상자로, 선은 선 도형으로 넣는다.
- 시험: 결과 zip 안에 필수 파트(mimetype, Contents/section0.xml, header.xml 등)가 있고 XML 이 잘 짜여 있으며 이름 문자열을 담고 있다.
- 실제로 한글에서 열리는지는 운영자 PC 에서 확인한다(개발 PC 에는 한글이 없다).

### Task 8: hwp · hwpx · pdf 리더

hwp 샘플이 없으므로 시험은 PDF(reportlab 으로 만든 표)와 hwpx(Task 7 의 출력 구조)로 한다. hwp 리더는 olefile 로 BodyText 를 풀어 문단 텍스트를 뽑는 데까지 만들고, 샘플을 받은 뒤 검증한다.

### Task 9: exe 묶기

PyInstaller onedir 로 묶는다. 만든 exe 를 실제로 실행해 창이 뜨는지 확인하고, 폴더를 zip 으로 압축한다.
