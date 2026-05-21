"""Render card JPEGs from plan + theme YAML (Pillow). 템플릿2(본문).txt 규격 반영."""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import yaml
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
THEMES_DIR = ROOT / "themes"
WINDOWS_MALGUN = Path(r"C:\Windows\Fonts\malgun.ttf")
WINDOWS_MALGUN_BD = Path(r"C:\Windows\Fonts\malgunbd.ttf")


@dataclass
class RenderOptions:
    theme_id: str = "mofe_body"
    font_scale: float = 1.0
    title_color: str | None = None
    body_color: str | None = None
    logo_position: str = "top_right"
    character_png: bytes | None = None
    logo_png: bytes | None = None
    # 템플릿2 §2-2: 녹/파/보/주황 섹션 톤
    section_tone: str = "blue"
    # 템플릿2 §6: simple=여백형, white_card=패턴B 큰 흰 카드
    body_layout: str = "simple"


def _load_theme(theme_id: str) -> dict[str, Any]:
    path = THEMES_DIR / f"{theme_id}.yaml"
    if not path.exists():
        path = THEMES_DIR / "mofe_body.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    sz = max(11, int(size))
    paths = [WINDOWS_MALGUN_BD, WINDOWS_MALGUN] if bold else [WINDOWS_MALGUN, WINDOWS_MALGUN_BD]
    for p in paths:
        if p.exists():
            try:
                return ImageFont.truetype(str(p), sz)
            except OSError:
                continue
    return ImageFont.load_default()


def _scale(n: float, factor: float) -> int:
    return max(10, int(n * factor))


def _line_height(font: ImageFont.ImageFont) -> int:
    if hasattr(font, "getbbox"):
        b = font.getbbox("Ay가")
        return b[3] - b[1] + 6
    return (getattr(font, "size", 14) or 14) + 6


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def _tone(theme: dict[str, Any], tone_key: str) -> dict[str, str]:
    tones = theme.get("section_tones") or {}
    t = tones.get(tone_key) or tones.get("neutral") or {"stripe": "#4D99D8", "title_on_page": "#111111"}
    return {"stripe": str(t.get("stripe", "#4D99D8")), "title_on_page": str(t.get("title_on_page", "#111111"))}


def section_tone_palette(theme_id: str, tone_key: str) -> dict[str, str]:
    """섹션 톤별 stripe·제목 강조색 (이미지 프롬프트·Pillow 렌더 공용)."""
    return _tone(_load_theme(theme_id), tone_key)


def _draw_text_block(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: str,
    *,
    align: str = "left",
) -> None:
    x0, y0, x1, y1 = xy
    w = x1 - x0
    approx = max(6, w // max(10, _line_height(font)))
    lines = textwrap.wrap(text, width=approx) if text else [""]
    y = y0
    lh = _line_height(font)
    for line in lines:
        if y + lh > y1:
            break
        if align == "center":
            tw = _text_width(draw, line, font)
            draw.text((x0 + (w - tw) // 2, y), line, font=font, fill=fill)
        else:
            draw.text((x0, y), line, font=font, fill=fill)
        y += lh


def _rounded_rect(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    radius: int,
    *,
    fill: str,
    outline: str | None = None,
    width: int = 1,
) -> None:
    if hasattr(draw, "rounded_rectangle"):
        draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)
    else:
        draw.rectangle(xy, fill=fill, outline=outline, width=width)


def _draw_capsule_label(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text: str,
    font: ImageFont.ImageFont,
    text_color: str,
    bg: str,
    radius: int,
    pad_x: int = 18,
    pad_y: int = 10,
) -> int:
    """흰 캡슐 라벨 (템플릿2 §4). 반환값: 사용한 높이."""
    if not text.strip():
        return 0
    tw = _text_width(draw, text, font)
    w, h = tw + 2 * pad_x, _line_height(font) + 2 * pad_y - 6
    _rounded_rect(draw, (x, y, x + w, y + h), radius, fill=bg, outline=None)
    draw.text((x + pad_x, y + pad_y - 2), text, font=font, fill=text_color)
    return h + 8


def _paste_logo(
    base: Image.Image,
    logo_bytes: bytes | None,
    theme: dict[str, Any],
    position: str,
) -> None:
    if not logo_bytes:
        return
    try:
        logo = Image.open(BytesIO(logo_bytes)).convert("RGBA")
    except OSError:
        return
    boxes = theme.get("logo_box") or {}
    key = position if position in boxes else "top_right"
    box = boxes.get(key) or boxes.get("top_right") or [588, 40, 160, 56]
    bx0, by0, bw, bh = int(box[0]), int(box[1]), int(box[2]), int(box[3])
    logo.thumbnail((bw, bh), Image.Resampling.LANCZOS)
    lw, lh = logo.size
    if key == "top_right":
        x = bx0 + bw - lw
        y = by0
    elif key == "bottom_center":
        x = bx0 + (bw - lw) // 2
        y = by0 + (bh - lh) // 2
    else:
        x = bx0
        y = by0
    base.paste(logo, (x, y), logo)


def paste_logo_on_image(
    base: Image.Image,
    logo_bytes: bytes | None,
    *,
    theme_id: str = "mofe_body",
    logo_position: str = "bottom_center",
) -> Image.Image:
    """생성된 카드 JPEG/RGB 이미지 위에 로고 PNG 합성."""
    if not logo_bytes:
        return base
    theme = _load_theme(theme_id)
    out = base.copy()
    _paste_logo(out, logo_bytes, theme, logo_position)
    return out


def _paste_character(base: Image.Image, char_bytes: bytes | None, theme: dict[str, Any]) -> None:
    if not char_bytes:
        return
    try:
        ch = Image.open(BytesIO(char_bytes)).convert("RGBA")
    except OSError:
        return
    slot = (theme.get("character_slot") or {}).get("bottom_right") or [480, 620, 280, 340]
    sx, sy, sw, sh = int(slot[0]), int(slot[1]), int(slot[2]), int(slot[3])
    ch.thumbnail((sw, sh), Image.Resampling.LANCZOS)
    cw, ch_ = ch.size
    base.paste(ch, (sx, sy + sh - ch_), ch)


def _paste_slot_illustration(base: Image.Image, png_bytes: bytes | None, theme: dict[str, Any]) -> None:
    """AI 생성 일러스트를 character_slot에 배치 (텍스트는 이후에 그려 덮음)."""
    if not png_bytes:
        return
    try:
        im = Image.open(BytesIO(png_bytes)).convert("RGBA")
    except OSError:
        return
    slot = (theme.get("character_slot") or {}).get("bottom_right") or [480, 620, 280, 340]
    sx, sy, sw, sh = int(slot[0]), int(slot[1]), int(slot[2]), int(slot[3])
    im.thumbnail((sw, sh), Image.Resampling.LANCZOS)
    cw, ch_ = im.size
    base.paste(im, (sx, sy + sh - ch_), im)


def render_slide(
    slide: dict[str, Any],
    *,
    plan: dict[str, Any],
    theme: dict[str, Any],
    options: RenderOptions,
    illustration_png: bytes | None = None,
) -> Image.Image:
    role = slide.get("role", "body")
    variants = theme.get("variants") or {}
    v = variants.get(role) or variants.get("body") or {}
    canvas = theme.get("canvas") or {"width": 800, "height": 1000}
    w, h = int(canvas["width"]), int(canvas["height"])
    mg = theme.get("margins") or {"x": 60, "y": 48, "bottom_reserve": 78}
    mx = int(mg.get("x", 60))
    my = int(mg.get("y", 48))
    br = int(mg.get("bottom_reserve", 78))
    pal = theme.get("palette") or {}
    sizes = theme.get("sizes") or {}
    layout = theme.get("layout") or {}
    fs = options.font_scale
    tone = _tone(theme, options.section_tone)
    stripe = tone["stripe"]
    tone_title = options.title_color or tone["title_on_page"]
    body_c = options.body_color or pal.get("body", "#333333")
    page_bg = v.get("background") or pal.get("page_bg", "#F6F8F3")
    img = Image.new("RGB", (w, h), page_bg)
    if illustration_png:
        _paste_slot_illustration(img, illustration_png, theme)
    draw = ImageDraw.Draw(img)
    subtle = pal.get("subtle", "#666666")
    foot_c = pal.get("footnote", "#777777")
    cap_bg = pal.get("capsule_bg", "#FFFFFF")
    cap_tx = pal.get("capsule_text", "#111111")
    on_stripe = pal.get("on_stripe", "#FFFFFF")
    cap_r = int(layout.get("capsule_radius", 22))

    if role == "cover":
        band_h = int(layout.get("cover_band_height", 200))
        draw.rectangle([0, 0, w, band_h], fill=stripe)
        f_ser = _font(_scale(sizes.get("cover_series_on_band", 26), fs), bold=True)
        f_head = _font(_scale(sizes.get("cover_head", 22), fs))
        f_st = _font(_scale(sizes.get("cover_slide_title", 44), fs), bold=True)
        series = plan.get("series_title", "")
        hc = plan.get("head_copy", "")
        _draw_text_block(draw, (mx, 36, w - mx - 100, band_h - 8), series, f_ser, on_stripe)
        _draw_text_block(draw, (mx, band_h + 20, w - mx, band_h + 80), hc, f_head, body_c)
        _draw_text_block(draw, (mx, band_h + 100, w - mx, h - br - 40), slide.get("title", ""), f_st, tone_title, align="center")
    elif role == "closing":
        f_t = _font(_scale(sizes.get("closing_main", 34), fs), bold=True)
        f_f = _font(_scale(sizes.get("footnote", 18), fs))
        title = slide.get("title", "")
        bullets = slide.get("bullets") or []
        block = title
        if bullets:
            block = block + "\n\n" + "\n".join(bullets)
        y1, y2 = my + 80, h - br - 50
        _draw_text_block(draw, (mx + 16, y1, w - mx - 16, y2), block, f_t, tone_title, align="center")
        if slide.get("footnote"):
            _draw_text_block(
                draw,
                (mx, h - br - 40, w - mx, h - 8),
                str(slide["footnote"]),
                f_f,
                foot_c,
                align="center",
            )
    else:
        # 본문 — 템플릿2 §1, §6
        stripe_h = int(layout.get("top_stripe_height", 6))
        draw.rectangle([0, 0, w, stripe_h], fill=stripe)

        f_series = _font(_scale(sizes.get("series_capsule", 23), fs), bold=True)
        f_hc = _font(_scale(sizes.get("head_copy_small", 21), fs))
        f_main = _font(_scale(sizes.get("main_title", 48), fs), bold=True)
        f_bul = _font(_scale(sizes.get("bullet", 31), fs))
        f_fn = _font(_scale(sizes.get("footnote", 20), fs))

        cy = my
        series = plan.get("series_title", "") or "시리즈"
        used = _draw_capsule_label(draw, mx, cy, series, f_series, cap_tx, cap_bg, cap_r)
        cy += used
        hc = plan.get("head_copy", "")
        if hc:
            _draw_text_block(draw, (mx, cy, w - mx, cy + 40), hc, f_hc, subtle)
            cy += 36

        content_top = cy + 12
        if options.body_layout == "white_card":
            cx = int(layout.get("white_card_margin_x", 52))
            cty = int(layout.get("white_card_top", 168))
            cw_ = int(layout.get("white_card_width", 696))
            ch_ = int(layout.get("white_card_height", 720))
            cr = int(layout.get("white_card_radius", 26))
            _rounded_rect(
                draw,
                (cx, cty, cx + cw_, cty + ch_),
                cr,
                fill=pal.get("card_white", "#FFFFFF"),
                outline="#E8EBE4",
                width=1,
            )
            inner_mx, inner_my = cx + 24, cty + 28
            inner_w = cx + cw_ - 24
            _draw_text_block(
                draw,
                (inner_mx, inner_my, inner_w, cty + ch_ - 24),
                slide.get("title", ""),
                f_main,
                tone_title,
            )
            yb = inner_my + _line_height(f_main) * 3
            for b in slide.get("bullets") or []:
                line = f"· {b}"
                _draw_text_block(draw, (inner_mx, yb, inner_w, yb + 120), line, f_bul, body_c)
                yb += min(100, _line_height(f_bul) * 2 + 16)
                if yb > cty + ch_ - 50:
                    break
        else:
            _draw_text_block(draw, (mx, content_top, w - mx, content_top + 140), slide.get("title", ""), f_main, tone_title)
            yb = content_top + 150
            for b in slide.get("bullets") or []:
                line = f"· {b}"
                _draw_text_block(draw, (mx, yb, w - mx, yb + 110), line, f_bul, body_c)
                yb += min(96, _line_height(f_bul) * 2 + 12)
                if yb > h - br - 40:
                    break
            if slide.get("footnote"):
                _draw_text_block(draw, (mx, h - br - 32, w - mx, h - 10), str(slide["footnote"]), f_fn, foot_c)

        if options.body_layout == "white_card" and slide.get("footnote"):
            _draw_text_block(draw, (mx, h - br - 28, w - mx, h - 6), str(slide["footnote"]), f_fn, foot_c)

    _paste_logo(img, options.logo_png, theme, options.logo_position)
    if not illustration_png:
        _paste_character(img, options.character_png, theme)
    return img


def render_plan_to_jpegs(
    plan_dict: dict[str, Any],
    out_dir: Path,
    options: RenderOptions,
    *,
    quality: int = 95,
    progress_callback: Any | None = None,
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    theme = _load_theme(options.theme_id)
    paths: list[Path] = []
    slides = plan_dict.get("slides") or []
    total = len(slides)

    for i, slide in enumerate(slides):
        img = render_slide(
            slide,
            plan=plan_dict,
            theme=theme,
            options=options,
            illustration_png=None,
        )
        role = slide.get("role", "body")
        fname = f"{i + 1:02d}_{role}.jpg"
        p = out_dir / fname
        img.save(p, format="JPEG", quality=quality, optimize=True)
        paths.append(p)
        if progress_callback is not None:
            progress_callback(i + 1, total)
    return paths


def list_theme_ids() -> list[str]:
    if not THEMES_DIR.exists():
        return ["mofe_body"]
    ids = sorted(p.stem for p in THEMES_DIR.glob("*.yaml"))
    if "mofe_body" in ids:
        ids.remove("mofe_body")
        return ["mofe_body"] + ids
    return ids
