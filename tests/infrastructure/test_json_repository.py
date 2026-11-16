from datetime import date

import pytest

from kendo_tournament.application.draw_brackets import draw_all, rebuild_divisions
from kendo_tournament.domain.draw.editing import withdraw
from kendo_tournament.domain.model import DivisionRule, Event, Gender, Grade, Participant, Team
from kendo_tournament.domain.tournament import Scope, Tournament
from kendo_tournament.infrastructure.storage.json_codec import UnreadableTournamentFile
from kendo_tournament.infrastructure.storage.json_repository import JsonTournamentRepository


def sample_tournament():
    t = Tournament("시험 대회", date(2026, 11, 21), Scope.NATIONAL)
    t.participants = [
        Participant(str(i), f"선수{i}", Gender.MALE, f"도장{i % 3}", Grade(13), 30, "광명", "a.docx") for i in range(7)
    ]
    t.teams = [Team("t1", "도장0 A", "도장0", ("0", "3"))]
    t.rules = [DivisionRule("r", Event.INDIVIDUAL, Gender.MALE, Grade(13), Grade(13))]
    t.merge_dojangs(["도장 1"], "도장2")
    rebuild_divisions(t)
    draw_all(t)
    label = t.divisions[0].label
    occupied = next(i for i, e in enumerate(t.brackets[label].slots) if e is not None)
    t.brackets[label] = withdraw(t.brackets[label], occupied).with_title("남자 성인 개인전 A조")
    return t


def test_저장했다가_불러오면_손으로_고친_대진까지_그대로다(tmp_path):
    original = sample_tournament()
    repo = JsonTournamentRepository()
    path = tmp_path / "대회.kendo"
    repo.save(original, path)
    loaded = repo.load(path)
    assert loaded == original


def test_모르는_형식이나_손상된_파일은_알아듣게_거부한다(tmp_path):
    repo = JsonTournamentRepository()
    broken = tmp_path / "깨짐.kendo"
    broken.write_text("{ 이건 json 이 아님", encoding="utf-8")
    with pytest.raises(UnreadableTournamentFile):
        repo.load(broken)
    future = tmp_path / "미래.kendo"
    future.write_text('{"format_version": 99}', encoding="utf-8")
    with pytest.raises(UnreadableTournamentFile, match="버전"):
        repo.load(future)


def test_합치는_방향을_적어_둔_예전_파일도_열린다(tmp_path):
    import json

    repo = JsonTournamentRepository()
    path = tmp_path / "예전.kendo"
    repo.save(sample_tournament(), path)
    saved = json.loads(path.read_text(encoding="utf-8"))
    for rule in saved["rules"]:
        rule["merge_direction"] = "UP"
    path.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
    assert repo.load(path).rules == sample_tournament().rules


def test_인쇄_순서와_새_쪽_설정이_저장되고_없던_예전_파일도_열린다(tmp_path):
    import json

    repo = JsonTournamentRepository()
    original = sample_tournament()
    original.print_order = [original.divisions[0].label]
    original.page_breaks = [original.divisions[0].label]
    path = tmp_path / "대회.kendo"
    repo.save(original, path)
    assert repo.load(path) == original

    saved = json.loads(path.read_text(encoding="utf-8"))
    del saved["print_order"], saved["page_breaks"]
    path.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
    loaded = repo.load(path)
    assert loaded.print_order == [] and loaded.page_breaks == []


def test_3위_결정전_설정이_적힌_예전_파일도_열린다(tmp_path):
    import json

    repo = JsonTournamentRepository()
    path = tmp_path / "예전.kendo"
    original = sample_tournament()
    repo.save(original, path)
    saved = json.loads(path.read_text(encoding="utf-8"))
    saved["third_place_match"] = True
    path.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
    assert repo.load(path) == original


def test_디자인_표지_설정이_든_예전_파일도_열리고_그_설정은_버린다(tmp_path):
    import json

    repo = JsonTournamentRepository()
    path = tmp_path / "대회.kendo"
    original = sample_tournament()
    repo.save(original, path)
    saved = json.loads(path.read_text(encoding="utf-8"))
    saved["book"].update(title="옛 제목", color="#0047a0", cover_seed=3, accent="#c9a24a", third="")
    path.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
    assert repo.load(path) == original
    repo.save(repo.load(path), path)
    assert "cover_seed" not in json.loads(path.read_text(encoding="utf-8"))["book"]


def test_가져온_표지_경로는_저장되고_예전_파일은_디자인_표지로_읽힌다(tmp_path):
    import json
    from dataclasses import replace

    repo = JsonTournamentRepository()
    path = tmp_path / "대회.kendo"
    original = sample_tournament()
    original.book = replace(original.book, cover_file="C:/표지/만들어온표지.pdf")
    repo.save(original, path)
    assert repo.load(path).book.cover_file == "C:/표지/만들어온표지.pdf"

    saved = json.loads(path.read_text(encoding="utf-8"))
    del saved["book"]["cover_file"]
    path.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
    assert repo.load(path).book.cover_file == ""


def test_성인_나이_구간은_저장되고_없던_예전_파일은_나이로_안_나눈_규칙으로_읽힌다(tmp_path):
    import json

    repo = JsonTournamentRepository()
    tournament = sample_tournament()
    adult = Grade(13)
    tournament.rules.append(DivisionRule("청", Event.INDIVIDUAL, Gender.MALE, adult, adult, None, None, 20, 35, "청년부"))
    path = tmp_path / "나이.kendo"
    repo.save(tournament, path)
    assert repo.load(path).rules[-1].age_band_label == "청년부(20~35세)"
    saved = json.loads(path.read_text(encoding="utf-8"))
    for rule in saved["rules"]:
        for key in ("age_from", "age_to", "age_name"):
            rule.pop(key)
    path.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
    assert not any(rule.has_age_band for rule in repo.load(path).rules)


def test_책자_앞쪽_내용과_뒤표지는_저장되고_예전_파일은_기본_틀로_읽힌다(tmp_path):
    import json
    from dataclasses import replace

    from kendo_tournament.domain.program import DEFAULT_PROGRAM

    repo = JsonTournamentRepository()
    tournament = sample_tournament()
    program = replace(DEFAULT_PROGRAM, officials=(("대회장", "김가람"),), courts=(("제1경기장", "가, 나"),))
    tournament.book = replace(tournament.book, program=program, back_cover_file="뒤.pdf")
    path = tmp_path / "책자.kendo"
    repo.save(tournament, path)
    loaded = repo.load(path).book
    assert loaded.program == program and loaded.back_cover_file == "뒤.pdf"
    saved = json.loads(path.read_text(encoding="utf-8"))
    del saved["book"]["program"], saved["book"]["back_cover_file"]
    path.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
    old = repo.load(path).book
    assert old.program == DEFAULT_PROGRAM and old.back_cover_file == ""


def test_없어진_경기도_범위로_저장한_예전_파일은_광명_범위로_열린다(tmp_path):
    import json

    repo = JsonTournamentRepository()
    path = tmp_path / "예전.kendo"
    repo.save(sample_tournament(), path)
    saved = json.loads(path.read_text(encoding="utf-8"))
    saved["scope"] = "GYEONGGI"
    path.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
    assert repo.load(path).scope is Scope.GWANGMYEONG


def test_대회_범위는_전국과_광명뿐이다():
    assert [scope.value for scope in Scope] == ["전국", "광명"]


def test_팀원_이름_넣기는_저장되고_없던_예전_파일은_켠_것으로_읽힌다(tmp_path):
    import json
    from dataclasses import replace

    repo = JsonTournamentRepository()
    path = tmp_path / "대회.kendo"
    t = sample_tournament()
    t.book = replace(t.book, team_members=False)
    repo.save(t, path)
    assert repo.load(path).book.team_members is False
    saved = json.loads(path.read_text(encoding="utf-8"))
    del saved["book"]["team_members"]
    path.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
    assert repo.load(path).book.team_members is True


def test_팀_표시가_없던_예전_파일도_팀_칸은_팀으로_읽힌다(tmp_path):
    import json

    from kendo_tournament.domain.model import Entry

    repo = JsonTournamentRepository()
    path = tmp_path / "예전.kendo"
    t = sample_tournament()
    team_entry = Entry("t1", "A", "도장0", team=True)
    label = t.divisions[0].label
    t.brackets[label] = t.brackets[label].__class__(t.brackets[label].title, (team_entry, None), 1)
    repo.save(t, path)
    saved = json.loads(path.read_text(encoding="utf-8"))
    for slot in saved["brackets"][label]["slots"]:
        if slot:
            slot.pop("team", None)
    path.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
    assert repo.load(path).brackets[label].slots[0] == team_entry


def test_팀_종별은_저장되고_없던_예전_파일은_빈_종별로_읽힌다(tmp_path):
    import json
    from dataclasses import replace

    repo = JsonTournamentRepository()
    path = tmp_path / "대회.kendo"
    t = sample_tournament()
    t.teams = [replace(t.teams[0], category="남청소년부(중,고)")]
    repo.save(t, path)
    assert repo.load(path).teams[0].category == "남청소년부(중,고)"
    saved = json.loads(path.read_text(encoding="utf-8"))
    del saved["teams"][0]["category"]
    path.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
    assert repo.load(path).teams[0].category == ""


def test_개인전_종별은_저장되고_없던_예전_파일은_빈_종별로_읽힌다(tmp_path):
    import json
    from dataclasses import replace

    repo = JsonTournamentRepository()
    path = tmp_path / "대회.kendo"
    t = sample_tournament()
    t.participants = [replace(t.participants[0], category="남초등 1~2학년"), *t.participants[1:]]
    repo.save(t, path)
    assert repo.load(path).participants[0].category == "남초등 1~2학년"
    saved = json.loads(path.read_text(encoding="utf-8"))
    for person in saved["participants"]:
        del person["category"]
    path.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
    assert all(p.category == "" for p in repo.load(path).participants)


def test_대회_종별_표는_저장되고_없던_예전_파일은_광명_회장기_종별로_읽힌다(tmp_path):
    import json

    from kendo_tournament.domain.division.category_table import DEFAULT_CATEGORY_TABLE, GWANGMYEONG_MAYOR

    repo = JsonTournamentRepository()
    path = tmp_path / "대회.kendo"
    t = sample_tournament()
    t.categories = GWANGMYEONG_MAYOR
    repo.save(t, path)
    assert repo.load(path).categories == GWANGMYEONG_MAYOR
    saved = json.loads(path.read_text(encoding="utf-8"))
    del saved["categories"]
    path.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
    assert repo.load(path).categories == DEFAULT_CATEGORY_TABLE


def test_대회사는_저장되고_없던_예전_파일은_기본_틀로_읽힌다(tmp_path):
    import json
    from dataclasses import replace

    from kendo_tournament.domain.greeting import DEFAULT_GREETING, Greeting

    repo = JsonTournamentRepository()
    path = tmp_path / "대회.kendo"
    t = sample_tournament()
    greeting = Greeting(body="본문", date_text="2026. 4. 12", position="회장", name="김가람", photo_file="사진.png")
    t.book = replace(t.book, greeting=greeting)
    repo.save(t, path)
    assert repo.load(path).book.greeting == greeting
    saved = json.loads(path.read_text(encoding="utf-8"))
    del saved["book"]["greeting"]
    path.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
    assert repo.load(path).book.greeting == DEFAULT_GREETING


def test_사진_표지_설정은_저장되고_없던_예전_파일은_사진_없이_읽힌다(tmp_path):
    import json
    from dataclasses import replace

    from kendo_tournament.domain.photo_cover import PhotoCoverSettings

    repo = JsonTournamentRepository()
    path = tmp_path / "대회.kendo"
    t = sample_tournament()
    cover = PhotoCoverSettings(photo="표지.jpg", back_photo="뒤.jpg", title_lines="제1회\n대회", venue="광명고")
    t.book = replace(t.book, photo_cover=cover)
    repo.save(t, path)
    assert repo.load(path).book.photo_cover == cover
    saved = json.loads(path.read_text(encoding="utf-8"))
    del saved["book"]["photo_cover"]
    path.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
    assert repo.load(path).book.photo_cover == PhotoCoverSettings()


def test_전국_대회의_대회사_선택과_파일이_저장되고_예전_파일은_고르지_않은_것으로_읽힌다(tmp_path):
    import json
    from dataclasses import replace

    from kendo_tournament.domain.book import GreetingSource

    repo = JsonTournamentRepository()
    path = tmp_path / "대회.kendo"
    t = sample_tournament()
    t.book = replace(t.book, greeting_source=GreetingSource.FILE, greeting_file="회장인사.pdf")
    repo.save(t, path)
    loaded = repo.load(path).book
    assert loaded.greeting_source is GreetingSource.FILE and loaded.greeting_file == "회장인사.pdf"
    saved = json.loads(path.read_text(encoding="utf-8"))
    del saved["book"]["greeting_source"], saved["book"]["greeting_file"]
    path.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
    assert repo.load(path).book.greeting_source is None


def test_팀원_자리는_저장되고_없던_예전_파일은_자리_없이_읽힌다(tmp_path):
    import json
    from dataclasses import replace

    repo = JsonTournamentRepository()
    path = tmp_path / "대회.kendo"
    t = sample_tournament()
    team = t.teams[0]
    positions = tuple(["선봉", "중견", "주장", "후보", "후보"][: len(team.member_ids)])
    t.teams = [replace(team, positions=positions)]
    repo.save(t, path)
    assert repo.load(path).teams[0].positions == positions
    saved = json.loads(path.read_text(encoding="utf-8"))
    del saved["teams"][0]["positions"]
    path.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
    assert repo.load(path).teams[0].positions == ()
