"""한글 OWPML(.hwpx) 신청서 리더. hwpx 는 zip 안에 XML 이 든 형식이다."""

from __future__ import annotations

import re
import zipfile
from collections.abc import Iterator
from pathlib import Path
from xml.etree import ElementTree

from kendo_tournament.domain.ports import ReadResult
from kendo_tournament.infrastructure.readers.document_text import Block, Paragraph, Table, blocks_to_result

_SECTION = re.compile(r"^Contents/section(\d+)\.xml$")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text_without_tables(element: ElementTree.Element) -> str:
    parts = []
    for child in element:
        name = _local(child.tag)
        if name == "tbl":
            continue
        if name == "t":
            parts.append("".join(child.itertext()))
        else:
            parts.append(_text_without_tables(child))
    return "".join(parts)


def _cell_text(cell: ElementTree.Element) -> str:
    paragraphs = [p for p in cell.iter() if _local(p.tag) == "p"]
    return " ".join(t for t in ("".join(p.itertext()).strip() for p in paragraphs) if t)


def _table(element: ElementTree.Element) -> Table:
    rows = []
    for row in element:
        if _local(row.tag) != "tr":
            continue
        rows.append(tuple(_cell_text(cell) for cell in row if _local(cell.tag) == "tc"))
    return Table(tuple(rows))


def _walk(element: ElementTree.Element) -> Iterator[Block]:
    for child in element:
        name = _local(child.tag)
        if name == "tbl":
            yield _table(child)
        elif name == "p":
            text = _text_without_tables(child).strip()
            if text:
                yield Paragraph(text)
            yield from (block for block in _walk(child) if isinstance(block, Table))
        else:
            yield from _walk(child)


def _section_names(archive: zipfile.ZipFile) -> list[str]:
    found = [(int(m.group(1)), name) for name in archive.namelist() if (m := _SECTION.match(name))]
    return [name for _, name in sorted(found)]


def hwpx_blocks(path: Path) -> list[Block]:
    """hwpx 본문(구역 순서대로)의 문단과 표."""
    blocks: list[Block] = []
    with zipfile.ZipFile(path) as archive:
        for name in _section_names(archive):
            root = ElementTree.fromstring(archive.read(name))
            blocks.extend(_walk(root))
    return blocks


class HwpxReader:
    def read(self, path: Path) -> ReadResult:
        return blocks_to_result(hwpx_blocks(path), path.name)
