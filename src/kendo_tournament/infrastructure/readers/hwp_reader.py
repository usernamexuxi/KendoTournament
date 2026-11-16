"""한글 5.0 바이너리(.hwp) 신청서 리더.

한글 프로그램 없이 파일을 직접 푼다(ADR: 한글 비의존). 구조는 한컴이 공개한 「한글 문서 파일 형식 5.0」을 따른다.
실제 신청서 샘플로 아직 검증하지 못했다 — 샘플을 받으면 tests/infrastructure 에 시험을 추가한다.
"""

from __future__ import annotations

import struct
import zlib
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import olefile

from kendo_tournament.domain.ports import ReadResult
from kendo_tournament.infrastructure.readers.document_text import Block, Paragraph, Table, blocks_to_result

TAG_PARA_TEXT = 67
TAG_CTRL_HEADER = 71
TAG_LIST_HEADER = 72
TAG_TABLE = 77
TABLE_CTRL_ID = b" lbt"
FLAG_COMPRESSED = 0x01
FLAG_PASSWORD = 0x02
SINGLE_WCHAR_CONTROLS = {0, 10, 13, *range(24, 32)}
WIDE_CONTROL_WCHARS = 8
TAB = 9
CELL_ADDRESS_OFFSETS = (8, 6)


class HwpReadError(Exception):
    pass


@dataclass(frozen=True)
class Record:
    tag: int
    level: int
    data: bytes


def parse_records(stream: bytes) -> list[Record]:
    records, offset = [], 0
    while offset + 4 <= len(stream):
        (header,) = struct.unpack_from("<I", stream, offset)
        offset += 4
        tag, level, size = header & 0x3FF, (header >> 10) & 0x3FF, (header >> 20) & 0xFFF
        if size == 0xFFF:
            (size,) = struct.unpack_from("<I", stream, offset)
            offset += 4
        records.append(Record(tag, level, stream[offset : offset + size]))
        offset += size
    return records


def para_text(data: bytes) -> str:
    """PARA_TEXT 의 UTF-16 글자에서 컨트롤 문자(표·그림 자리표시 등)를 걷어 낸다."""
    chars, index = [], 0
    count = len(data) // 2
    while index < count:
        (code,) = struct.unpack_from("<H", data, index * 2)
        if code >= 32:
            chars.append(chr(code))
            index += 1
        elif code in SINGLE_WCHAR_CONTROLS:
            index += 1
        else:
            if code == TAB:
                chars.append(" ")
            index += WIDE_CONTROL_WCHARS
    return "".join(chars)


def _cell_address(data: bytes, rows: int, cols: int) -> tuple[int, int] | None:
    for offset in CELL_ADDRESS_OFFSETS:
        if len(data) >= offset + 4:
            col, row = struct.unpack_from("<HH", data, offset)
            if col < cols and row < rows:
                return row, col
    return None


def _read_table(records: list[Record], start: int) -> tuple[Table, int]:
    """start 는 표 CTRL_HEADER 위치. (표, 표 다음 레코드 위치)를 돌려준다."""
    level = records[start].level
    rows = cols = 0
    cells: list[tuple[tuple[int, int] | None, list[str]]] = []
    index = start + 1
    while index < len(records) and records[index].level > level:
        record = records[index]
        if record.tag == TAG_TABLE and record.level == level + 1 and len(record.data) >= 8:
            rows, cols = struct.unpack_from("<HH", record.data, 4)
        elif record.tag == TAG_LIST_HEADER and record.level == level + 1:
            cells.append((_cell_address(record.data, rows, cols), []))
        elif record.tag == TAG_PARA_TEXT and cells:
            cells[-1][1].append(para_text(record.data).strip())
        index += 1
    grid = [["" for _ in range(cols)] for _ in range(rows)]
    for position, (address, texts) in enumerate(cells):
        row, col = address if address else divmod(position, max(cols, 1))
        if row < rows and col < cols:
            grid[row][col] = " ".join(t for t in texts if t)
    return Table(tuple(tuple(r) for r in grid)), index


def section_blocks(records: list[Record]) -> Iterator[Block]:
    index = 0
    while index < len(records):
        record = records[index]
        if record.tag == TAG_CTRL_HEADER and record.data[:4] == TABLE_CTRL_ID:
            table, index = _read_table(records, index)
            yield table
            continue
        if record.tag == TAG_PARA_TEXT:
            text = para_text(record.data).strip()
            if text:
                yield Paragraph(text)
        index += 1


def _section_streams(ole: olefile.OleFileIO) -> list[list[str]]:
    sections = [entry for entry in ole.listdir() if len(entry) == 2 and entry[0] == "BodyText"]
    return sorted(sections, key=lambda entry: int(entry[1].replace("Section", "") or 0))


class HwpPasswordError(HwpReadError):
    pass


def hwp_blocks(path: Path) -> list[Block]:
    """hwp 본문의 문단과 표. 한글 5.0 형식이 아니면 HwpReadError, 암호가 걸렸으면 HwpPasswordError."""
    if not olefile.isOleFile(str(path)):
        raise HwpReadError(f"{path.name}: 한글 5.0 형식(.hwp)이 아닙니다.")
    with olefile.OleFileIO(str(path)) as ole:
        header = ole.openstream("FileHeader").read()
        (flags,) = struct.unpack_from("<I", header, 36)
        if flags & FLAG_PASSWORD:
            raise HwpPasswordError(f"{path.name}: 암호가 걸린 한글 파일은 읽을 수 없습니다.")
        blocks: list[Block] = []
        for stream in _section_streams(ole):
            raw = ole.openstream(stream).read()
            data = zlib.decompress(raw, -15) if flags & FLAG_COMPRESSED else raw
            blocks.extend(section_blocks(parse_records(data)))
    return blocks


class HwpReader:
    def read(self, path: Path) -> ReadResult:
        try:
            blocks = hwp_blocks(path)
        except HwpPasswordError as error:
            return ReadResult((), (), (str(error),))
        return blocks_to_result(blocks, path.name)
