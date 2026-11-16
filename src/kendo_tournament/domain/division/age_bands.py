"""성인부 나이 구간 글(「청년부 20-35」)을 읽고 쓴다. 부문 규칙 표의 「성인 나이」 칸이 쓴다.

실제 신청서 양식이 성인을 나이로 나누고(남자청년부 20~35세 · 장년부 36~47세 · 중년부 48세부터) 대회마다 나이가 달라
운영자가 규칙마다 글로 고칠 수 있게 한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_BAND = re.compile(r"^(?P<name>[^0-9]*?)\s*(?P<start>\d+)\s*[-~]\s*(?P<end>\d*)\s*세?$")


@dataclass(frozen=True)
class AgeBand:
    name: str
    start: int
    end: int | None


def parse_age_bands(text: str) -> list[AgeBand]:
    """쉼표로 나눈 「이름 시작-끝」 목록. 끝을 비우면 「시작 세부터」. 빈 글이면 나누지 않는다(빈 목록).

    알아볼 수 없는 칸이 있거나 구간이 겹치면 ValueError — 조용히 건너뛰면 그 나이 선수가 부문에서 빠진다.
    """
    bands = []
    for piece in (part.strip() for part in text.split(",")):
        if not piece:
            continue
        match = _BAND.match(piece)
        if match is None:
            raise ValueError(f"나이 구간을 알아볼 수 없습니다: 「{piece}」 (예: 청년부 20-35)")
        end = int(match["end"]) if match["end"] else None
        start = int(match["start"])
        if end is not None and end < start:
            raise ValueError(f"나이 구간의 끝이 시작보다 작습니다: 「{piece}」")
        bands.append(AgeBand(match["name"].strip(), start, end))
    _check_no_overlap(bands)
    return bands


def band_text(name: str, start: int | None, end: int | None) -> str:
    """규칙의 나이 구간을 고칠 수 있는 글로. 나이 없이 부 이름만 있으면(인제 「중년부」 단체전) 이름만, 둘 다 없으면 빈 글."""
    if start is None:
        return name
    return f"{name} {start}-{'' if end is None else end}".strip()


def rule_age(text: str) -> tuple[int | None, int | None, str]:
    """규칙 한 줄의 나이 칸을 (시작, 끝, 부 이름)으로. 숫자 없이 「중년부」만 적으면 나이 없이 부 이름만이다."""
    stripped = text.strip()
    if stripped and not any(char.isdigit() for char in stripped):
        return None, None, stripped
    band = single_band(stripped)
    return (band.start, band.end, band.name) if band else (None, None, "")


def single_band(text: str) -> AgeBand | None:
    """규칙 한 줄의 나이 칸. 비면 None, 둘 이상이면 ValueError(한 규칙은 한 구간)."""
    bands = parse_age_bands(text)
    if len(bands) > 1:
        raise ValueError(f"규칙 한 줄에는 나이 구간을 하나만 적습니다: 「{text}」")
    return bands[0] if bands else None


def _check_no_overlap(bands: list[AgeBand]) -> None:
    ordered = sorted(bands, key=lambda band: band.start)
    for before, after in zip(ordered, ordered[1:], strict=False):
        if before.end is None or before.end >= after.start:
            raise ValueError(f"나이 구간이 겹칩니다: {before.name or before.start} · {after.name or after.start}")
