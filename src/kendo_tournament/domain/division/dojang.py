"""같은 도장 판정."""

from __future__ import annotations

import re
from collections.abc import Mapping


def dojang_key(name: str, aliases: Mapping[str, str] | None = None) -> str:
    """공백을 모두 지운 이름을 키로 쓴다. 운영자가 묶은 도장은 aliases 로 대표 키에 모은다."""
    key = re.sub(r"\s+", "", name or "")
    if aliases and key in aliases:
        return aliases[key]
    return key
