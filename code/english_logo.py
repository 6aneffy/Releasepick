"""logo.png(한글) → 동일 크기·문자 높이의 영문 워드마크 PNG 생성."""

from __future__ import annotations

import io
import os
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CODE_DIR = Path(__file__).resolve().parent
ROOT9 = CODE_DIR.parent
REPO_ROOT = CODE_DIR.parent
LEGACY_ENGLISH_LOGO_PATH = ROOT9 / "국장님믿고갑조" / "재정경제부 영문로고 파일.png"
CACHED_EN_LOGO = ROOT9 / "data" / "logo_en_mofe.png"

ENGLISH_LINES = ("Ministry of Finance", "and Economy")
TEXT_COLOR = (89, 87, 87, 255)
EMBLEM_SPLIT_X = 272
PAD_X = 24


def resolve_ko_logo_path(explicit: Path | None = None) -> Path | None:
    if explicit is not None and explicit.is_file():
        return explicit
    for candidate in (
        REPO_ROOT / "logo.png",
        REPO_ROOT.parent / "logo.png",
        ROOT9 / "logo.png",
    ):
        if candidate.is_file():
            return candidate
    return None


def _is_legacy_english_logo_bytes(data: bytes) -> bool:
    try:
        return LEGACY_ENGLISH_LOGO_PATH.is_file() and data == LEGACY_ENGLISH_LOGO_PATH.read_bytes()
    except OSError:
        return False


def _load_bold_sans(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    win = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    for name in ("arialbd.ttf", "segoeuib.ttf", "malgunbd.ttf", "arial.ttf"):
        path = win / name
        if path.is_file():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _measure_korean_text_band(src_im: Image.Image, split_x: int) -> tuple[int, int, int]:
    """한글 워드마크 문자 영역 — (y0, height, max_width) 픽셀."""
    w, h = src_im.size
    text = src_im.crop((split_x, 0, w, h)).convert("RGBA")
    px = text.load()
    tw, th = text.size
    ys: list[int] = []
    xs: list[int] = []
    for y in range(th):
        for x in range(tw):
            r, g, b, a = px[x, y]
            if a > 20 and (r > 40 or g > 40 or b > 40):
                ys.append(y)
                xs.append(x)
    if not ys:
        return h // 4, h // 2, w - split_x - PAD_X * 2
    y0, y1 = min(ys), max(ys)
    x1 = max(xs)
    text_h = y1 - y0 + 1
    max_w = min(w - split_x - PAD_X - 8, x1 + 24)
    return y0, text_h, max_w


def _fit_english_font(
    lines: tuple[str, ...],
    target_h: int,
    max_w: int,
) -> tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, int]:
    """한글 문자 밴드 높이·폭 안에 맞는 최대 영문 폰트."""
    draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    best_font = _load_bold_sans(20)
    best_size = 20
    for fs in range(96, 14, -1):
        font = _load_bold_sans(fs)
        gap = max(2, fs // 8)
        total_h = 0
        line_w = 0
        for i, line in enumerate(lines):
            bb = draw.textbbox((0, 0), line, font=font)
            tw, th = bb[2] - bb[0], bb[3] - bb[1]
            line_w = max(line_w, tw)
            total_h += th
            if i:
                total_h += gap
        if total_h <= target_h and line_w <= max_w:
            best_font, best_size = font, fs
            break
    return best_font, best_size


def _make_black_transparent(im: Image.Image) -> Image.Image:
    from render_cards import _logo_make_background_transparent

    return _logo_make_background_transparent(im, threshold=40)


def build_english_logo_from_korean(
    ko_logo_path: Path | None = None,
    *,
    ko_logo_bytes: bytes | None = None,
) -> bytes | None:
    """한글 logo.png와 동일 픽셀 크기·문자 밴드·엠블럼 위치의 영문 워드마크."""
    src_im: Image.Image | None = None
    if ko_logo_bytes and not _is_legacy_english_logo_bytes(ko_logo_bytes):
        try:
            src_im = Image.open(io.BytesIO(ko_logo_bytes)).convert("RGBA")
        except OSError:
            src_im = None
    if src_im is None:
        src = resolve_ko_logo_path(ko_logo_path)
        if src is None or src.resolve() == LEGACY_ENGLISH_LOGO_PATH.resolve():
            return None
        try:
            src_im = Image.open(src).convert("RGBA")
        except OSError:
            return None

    w, h = src_im.size
    split = min(EMBLEM_SPLIT_X, w - 1)
    emblem = src_im.crop((0, 0, split, h))

    text_y0, text_h, max_text_w = _measure_korean_text_band(src_im, split)
    font, _ = _fit_english_font(ENGLISH_LINES, text_h, max_text_w)

    draw_probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    gap = max(2, getattr(font, "size", 20) // 8)
    line_metrics: list[tuple[str, tuple[int, int, int, int]]] = []
    block_h = 0
    block_w = 0
    for i, line in enumerate(ENGLISH_LINES):
        bb = draw_probe.textbbox((0, 0), line, font=font)
        line_metrics.append((line, bb))
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        block_w = max(block_w, tw)
        block_h += th
        if i:
            block_h += gap

    text_y = text_y0 + (text_h - block_h) // 2
    tx = split + PAD_X

    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    canvas.paste(emblem, (0, 0), emblem)
    td = ImageDraw.Draw(canvas)
    cy = text_y
    for i, (line, bb) in enumerate(line_metrics):
        td.text((tx - bb[0], cy - bb[1]), line, font=font, fill=TEXT_COLOR)
        cy += (bb[3] - bb[1]) + (gap if i < len(line_metrics) - 1 else 0)

    canvas = _make_black_transparent(canvas)
    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()


def write_cached_english_logo(ko_logo_path: Path | None = None) -> Path | None:
    data = build_english_logo_from_korean(ko_logo_path)
    if not data:
        return None
    CACHED_EN_LOGO.parent.mkdir(parents=True, exist_ok=True)
    CACHED_EN_LOGO.write_bytes(data)
    return CACHED_EN_LOGO


@lru_cache(maxsize=4)
def _cached_bytes(ko_mtime_ns: int, ko_path_str: str) -> bytes | None:
    return build_english_logo_from_korean(Path(ko_path_str))


def load_english_logo_bytes(
    ko_logo_path: Path | None = None,
    *,
    ko_logo_bytes: bytes | None = None,
) -> bytes | None:
    if ko_logo_bytes and not _is_legacy_english_logo_bytes(ko_logo_bytes):
        return build_english_logo_from_korean(ko_logo_bytes=ko_logo_bytes)
    src = resolve_ko_logo_path(ko_logo_path)
    if src is None:
        return None
    if src.resolve() == LEGACY_ENGLISH_LOGO_PATH.resolve():
        return None
    try:
        mtime = src.stat().st_mtime_ns
    except OSError:
        return build_english_logo_from_korean(src)
    return _cached_bytes(mtime, str(src.resolve()))
