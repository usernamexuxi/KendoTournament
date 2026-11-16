"""로고 그림의 흰 바탕을 지워 표지 사진에 그대로 얹히게 한다. 어두운 바탕용으로 글자를 흰색으로 바꾼 판도 만든다.

받은 마크가 투명 바탕이 아니라 흰 바탕으로 꽉 찬 PNG 였다. 그대로 얹으면 색 바탕 위에 흰 상자가 뜬다.
- 바깥 흰 바탕: 그림 가장자리에서 이어진 흰 칸만 지운다. 다만 엠블럼의 흰 붓 획은 바깥 흰 바탕과 붙어 있어,
  같은 줄에서 색(파랑·주황) 칸 사이에 낀 흰 칸은 엠블럼의 일부로 보고 남긴다.
  엠블럼 밖의 흰 칸은 바깥과 끊겨 있어도(글자 「ㅁ」·「O」 속) 지운다 — 남기면 어두운 바탕에서 흰 점으로 뜬다.
- 글자: 채도가 낮은 어두운 칸(글자와 그 가장자리 번짐)은 진하기를 투명도로 바꿔 매끄럽게 하고,
  어두운 바탕용 판에서는 같은 투명도로 흰색을 칠한다.
"""

from __future__ import annotations

from collections import deque
from io import BytesIO

from PIL import Image

WHITE_LEVEL = 235
NEUTRAL_SPREAD = 24
COLORED_SPREAD = 60
TEXT_DARKEST = 33
OPAQUE = 255
LIGHT_TEXT = (255, 255, 255)


def _colored_spans(image: Image.Image) -> list[tuple[int, int] | None]:
    """줄마다 색 칸이 처음·마지막으로 나오는 x. 색 칸이 없는 줄은 None."""
    pixels = image.load()
    spans: list[tuple[int, int] | None] = []
    for y in range(image.height):
        colored = [x for x in range(image.width) if max(pixels[x, y][:3]) - min(pixels[x, y][:3]) >= COLORED_SPREAD]
        spans.append((colored[0], colored[-1]) if colored else None)
    return spans


def _outside_white(image: Image.Image) -> set[tuple[int, int]]:
    width, height = image.size
    pixels = image.load()
    spans = _colored_spans(image)
    seen: set[tuple[int, int]] = set()
    queue = deque((x, y) for x in range(width) for y in (0, height - 1))
    queue.extend((x, y) for y in range(height) for x in (0, width - 1))
    while queue:
        x, y = queue.popleft()
        if (x, y) in seen or not (0 <= x < width and 0 <= y < height):
            continue
        r, g, b, _ = pixels[x, y]
        span = spans[y]
        if min(r, g, b) < WHITE_LEVEL or (span is not None and span[0] < x < span[1]):
            continue
        seen.add((x, y))
        queue.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    for y in range(height):
        span = spans[y]
        for x in range(width):
            outside_mark = span is None or not span[0] < x < span[1]
            if outside_mark and min(pixels[x, y][:3]) >= WHITE_LEVEL:
                seen.add((x, y))
    return seen


def _text_alpha(r: int, g: int, b: int) -> int | None:
    """글자 칸이면 투명도, 아니면 None. 글자는 채도가 낮고 흰색보다 어둡다."""
    if max(r, g, b) - min(r, g, b) >= NEUTRAL_SPREAD or min(r, g, b) >= WHITE_LEVEL:
        return None
    level = (r + g + b) / 3
    return min(OPAQUE, round((255 - level) / (255 - TEXT_DARKEST) * OPAQUE))


def _png(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def cut_out(png: bytes) -> tuple[bytes, bytes]:
    """(밝은 바탕용, 어두운 바탕용) PNG. 둘 다 바깥 흰 바탕이 투명하다."""
    source = Image.open(BytesIO(png)).convert("RGBA")
    background = _outside_white(source)
    light, dark = source.copy(), source.copy()
    light_pixels, dark_pixels = light.load(), dark.load()
    pixels = source.load()
    text_color = (TEXT_DARKEST, TEXT_DARKEST, TEXT_DARKEST)
    for y in range(source.height):
        for x in range(source.width):
            r, g, b, a = pixels[x, y]
            if (x, y) in background:
                light_pixels[x, y] = dark_pixels[x, y] = (r, g, b, 0)
                continue
            alpha = _text_alpha(r, g, b)
            if alpha is not None:
                light_pixels[x, y] = (*text_color, min(alpha, a))
                dark_pixels[x, y] = (*LIGHT_TEXT, min(alpha, a))
    return _png(light), _png(dark)
