"""OpenAI Images API — GPT Image 계열 슬라이드 일러스트.

최신 Image API 기준: GPT Image 모델(`gpt-image-2`, `gpt-image-1.5`, …)은
`response_format` 미지원 · 응답에 `b64_json` 기본 포함.
참고: https://developers.openai.com/api/docs/guides/image-generation
"""

from __future__ import annotations

import base64
import logging
from typing import Any
from urllib.request import urlopen

from openai import OpenAI

from content_filter import append_image_safety, assert_plan_safe
from render_cards import get_logo_box, section_tone_palette
from template_resources import load_body_template_text, load_cover_template_text

LOGO_POS_EN_LABELS: dict[str, str] = {
    "top_right": "top-right",
    "top_left": "top-left",
    "bottom_center": "bottom-center",
}


LOGO_POS_KO_LABELS: dict[str, str] = {
    "top_right": "우측 상단",
    "top_left": "좌측 상단",
    "bottom_center": "하단 중앙",
}

# 영문 카드 AI 로고에 쓸 공식 영문 기관명 (철자 고정)
ENGLISH_LOGO_WORDMARK = "Ministry of Finance and Economy"
KOREAN_LOGO_WORDMARK = "재정경제부"


def _logo_layout_tail(logo_pos: str, theme_id: str, *, copy_locale: str) -> str:
    """AI가 카드 이미지 안에 직접 그릴 로고 지시 (한·영 동일 스타일, 영문만 문구 변경)."""
    bx, by, bw, bh = get_logo_box(theme_id, logo_pos)
    x1, y1 = bx + bw, by + bh
    pad = 28
    if copy_locale == "en":
        pos = LOGO_POS_EN_LABELS.get(logo_pos, logo_pos)
        common = (
            "[ENGLISH IMAGE — AI-DRAWN LOGO]\n"
            f"Draw the official Republic of Korea ministry logo INSIDE the image at {pos} "
            f"(target area x={bx}–{x1}, y={by}–{y1} on 800×1000).\n"
            "- Same visual style as the Korean card-news government logo: circular red/white/blue "
            "taegeuk (sam-taegeuk) emblem on the left + horizontal gray sans-serif wordmark on the right.\n"
            f"- English wordmark text MUST be exactly: \"{ENGLISH_LOGO_WORDMARK}\" "
            "(spell and capitalize exactly; do NOT use Korean \"재정경제부\" or other English variants).\n"
            "- No black rectangle behind the logo; logo blends with the card background (transparent look).\n"
            "- No dashed boxes, 'logo area' labels, or placeholders.\n"
            "- Logo size and placement should match the Korean series (same corner/foot position).\n"
        )
    else:
        pos = LOGO_POS_KO_LABELS.get(logo_pos, logo_pos)
        common = (
            "[한국어 이미지 — AI 생성 로고]\n"
            f"이미지 안에 공식 정부 로고를 직접 그린다. 위치: {pos} "
            f"(영역 x={bx}~{x1}, y={by}~{y1}, 800×1000).\n"
            "- 삼태극(적·청·백) 원형 엠블럼 + 한글 워드마크 "
            f"「{KOREAN_LOGO_WORDMARK}」(logo.png 공식 스타일과 동일한 회색 고딕).\n"
            "- 검은 사각형 배경 없이 카드 배경과 자연스럽게 어우러지게.\n"
            "- placeholder·점선·'로고 영역' 문구 금지.\n"
        )
    if logo_pos == "bottom_center":
        safe_y = max(120, by - pad)
        if copy_locale == "en":
            layout = (
                f"[COPY SAFE ZONE]\n"
                f"- Logo at bottom center (y≥{by}); keep title/bullets/art above y≈{safe_y}.\n"
            )
        else:
            layout = (
                f"[문안 안전 영역]\n"
                f"- 로고는 하단 중앙(y≥{by}); 제목·불릿·일러스트는 y≈{safe_y} 위.\n"
            )
    elif logo_pos == "top_right":
        if copy_locale == "en":
            layout = (
                f"[COPY SAFE ZONE]\n"
                f"- Logo top-right (x≥{bx - pad}, y≤{y1 + pad}); copy/art elsewhere.\n"
            )
        else:
            layout = (
                f"[문안 안전 영역]\n"
                f"- 로고 우상단(x≥{bx - pad}, y≤{y1 + pad}); 문안·일러스트는 다른 영역.\n"
            )
    else:
        if copy_locale == "en":
            layout = (
                f"[COPY SAFE ZONE]\n"
                f"- Logo top-left (x≤{x1 + pad}, y≤{y1 + pad}); copy/art elsewhere.\n"
            )
        else:
            layout = (
                f"[문안 안전 영역]\n"
                f"- 로고 좌상단(x≤{x1 + pad}, y≤{y1 + pad}); 문안·일러스트는 다른 영역.\n"
            )
    return common + layout


def build_english_logo_layout_block(logo_pos: str, theme_id: str = "mofe_body") -> str:
    return _logo_layout_tail(logo_pos, theme_id, copy_locale="en")


def build_korean_logo_layout_block(logo_pos: str, theme_id: str = "mofe_body") -> str:
    return _logo_layout_tail(logo_pos, theme_id, copy_locale="ko")

SECTION_TONE_LABELS: dict[str, str] = {
    "neutral": "기본(블루)",
    "green": "녹색",
    "blue": "파랑",
    "purple": "보라",
    "orange": "주황",
}

logger = logging.getLogger(__name__)

# UI 라벨 → `images.generate` 의 model 값 (카드 전면 생성에 사용)
IMAGE_MODEL_OPTIONS: list[tuple[str, str]] = [
    ("GPT Image 2 (gpt-image-2)", "gpt-image-2"),
    ("GPT Image 1.5 (gpt-image-1.5)", "gpt-image-1.5"),
    ("GPT Image 1 (gpt-image-1)", "gpt-image-1"),
    ("GPT Image 1 Mini (gpt-image-1-mini)", "gpt-image-1-mini"),
]


def image_models_for_selectbox() -> list[str]:
    return [label for label, _ in IMAGE_MODEL_OPTIONS]


def resolve_model(label: str) -> str:
    for lab, mid in IMAGE_MODEL_OPTIONS:
        if lab == label:
            return mid
    return IMAGE_MODEL_OPTIONS[0][1]


def _decode_response(resp: Any) -> bytes | None:
    if not resp or not getattr(resp, "data", None):
        return None
    item = resp.data[0]
    b64 = getattr(item, "b64_json", None)
    if b64:
        return base64.b64decode(b64)
    url = getattr(item, "url", None)
    if url:
        with urlopen(url, timeout=120) as r:
            return r.read()
    return None


PROMPT_MAX_CHARS = 28_000


def _clip_middle(s: str, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    h = max_len // 2 - 40
    t = max_len - h - 40
    return s[:h] + "\n\n...[중간 생략]...\n\n" + s[-t:]


def build_theme_description(
    *,
    theme_id: str,
    section_tone: str,
    body_layout: str,
    font_scale: float,
    use_custom_title: bool,
    use_custom_body: bool,
    title_color: str,
    body_color: str,
    logo_pos: str,
) -> str:
    parts = [
        f"YAML_테마={theme_id}",
        f"섹션톤={section_tone}",
        f"본문레이아웃={'흰카드(B)' if body_layout == 'white_card' else '여백(A)'}",
        f"폰트배율={font_scale}",
        f"로고위치={logo_pos}",
    ]
    if use_custom_title:
        parts.append(f"제목색지정={title_color}")
    if use_custom_body:
        parts.append(f"본문색지정={body_color}")
    return " | ".join(parts)


def build_section_tone_prompt_block(
    section_tone: str,
    theme_id: str = "mofe_body",
    *,
    for_cover: bool,
    copy_locale: str = "ko",
) -> str:
    """섹션 컬러 톤을 hex·지시문으로 명시 (표지는 템플릿 기본 하늘색 예시보다 우선)."""
    pal = section_tone_palette(theme_id, section_tone)
    stripe = pal["stripe"]
    title_c = pal["title_on_page"]
    label = SECTION_TONE_LABELS.get(section_tone, section_tone)
    if copy_locale == "en":
        if for_cover:
            return (
                "[COVER COLOR TONE — OVERRIDES default sky-blue examples in the spec below]\n"
                f"User-selected section tone: {label} ({section_tone})\n"
                f"Top header band, keyword badges, accent shapes — primary color: {stripe}\n"
                f"Headline emphasis color: {title_c}\n"
                "Background: bright off-white or soft gradient harmonizing with this tone; "
                "do NOT use default navy/sky-blue campaign background if tone is green/purple/orange.\n"
            "Match inner pages in the same series.\n"
        )
        return (
            "[BODY COLOR TONE — REQUIRED]\n"
            f"Section tone: {label} — top stripe/accent: {stripe}, title emphasis: {title_c}\n"
        )
    if for_cover:
        return (
            "[표지 컬러 톤 — 최우선 · 아래 표지 템플릿의 하늘색/블루 예시보다 이 설정이 우선]\n"
            f"사용자 선택 섹션 톤: {label} ({section_tone})\n"
            f"상단 컬러 밴드·헤더 영역·키워드 배지·강조 도형·띠 색상(주색): {stripe}\n"
            f"표지 제목·헤드라인 강조색: {title_c}\n"
            "배경은 선택 톤과 조화되는 밝은 오프화이트 또는 연한 그라데이션으로 구성한다. "
            "녹색 톤이면 하늘색·네이비 기본 캠페인 배경을 쓰지 말 것.\n"
            "본문 페이지와 동일한 섹션 컬러로 시리즈 전체 톤을 통일한다.\n"
        )
    return (
        "[본문 컬러 톤 — 필수 반영]\n"
        f"섹션 톤: {label} — 상단 띠·액센트: {stripe}, 제목 강조: {title_c}\n"
    )


def build_first_card_image_prompt(
    plan: dict[str, Any],
    slide: dict[str, Any],
    *,
    cover_template_full: str,
    theme_desc: str,
    copy_locale: str = "ko",
    section_tone: str = "blue",
    theme_id: str = "mofe_body",
    logo_pos: str = "bottom_center",
    concept_style_block: str = "",
) -> str:
    bullets = slide.get("bullets") or []
    blines = "\n".join(f"- {b}" for b in bullets) if bullets else ("(no bullets)" if copy_locale == "en" else "(불릿 없음)")
    foot = slide.get("footnote") or ("(no footnote)" if copy_locale == "en" else "(각주 없음)")
    priority = (
        "[최우선 — 반드시 이미지에 반영할 문안]\n"
        f"시리즈명: {plan.get('series_title', '')}\n"
        f"헤드카피: {plan.get('head_copy', '')}\n"
        f"표지 슬라이드 제목: {slide.get('title', '')}\n"
        f"표지 보조 불릿:\n{blines}\n"
        f"각주: {foot}\n"
    )
    if copy_locale == "en":
        tail = (
            "\n[작업 지시]\n"
            "Create ONE finished policy card-news COVER image. "
            "Render ALL visible headline and body copy from [최우선] clearly in natural English. "
            "Follow the full [표지 디자인 규격] spec below for layout, colors, typography, margins, 3D elements, etc. "
            "The design spec text may be in Korean; apply it as visual/layout rules regardless of language. "
            "Draw the government logo per [ENGLISH IMAGE — AI-DRAWN LOGO]. Single professional image."
            + build_english_logo_layout_block(logo_pos, theme_id)
        )
    else:
        tail = (
            "\n[작업 지시]\n"
            "재정경제부 정책 카드뉴스 '표지' 1장을 생성한다. 위 [최우선] 문안을 한글로 선명하게 배치하고, "
            "[표지 컬러 톤]의 hex 색을 상단 밴드·배지·강조에 반드시 적용한다(템플릿 기본 하늘색 무시). "
            "[표지 디자인 규격]의 레이아웃·타이포·여백·3D요소·정부 로고 배치를 반영한다. "
            "단일 완성 이미지, 정책 홍보용, 과장 없이 전문적으로."
            + build_korean_logo_layout_block(logo_pos, theme_id)
        )
    tone_block = build_section_tone_prompt_block(
        section_tone, theme_id, for_cover=True, copy_locale=copy_locale
    )
    spec = _clip_middle(
        cover_template_full,
        PROMPT_MAX_CHARS - len(priority) - len(tone_block) - len(theme_desc) - len(tail) - 120,
    )
    concept_part = f"\n\n{concept_style_block.strip()}\n" if concept_style_block.strip() else ""
    body = _clip_middle(
        f"{priority}\n\n{tone_block}{concept_part}\n\n[표지 디자인 규격 — 레이아웃·구도 참고, 색상은 위 컬러 톤 우선]\n"
        f"{spec}\n\n[현재 디자인 설정]\n{theme_desc}{tail}",
        PROMPT_MAX_CHARS + 2000,
    )
    return append_image_safety(body)


def build_body_card_image_prompt(
    plan: dict[str, Any],
    slide: dict[str, Any],
    page_index_1based: int,
    *,
    body_template_full: str,
    theme_desc: str,
    copy_locale: str = "ko",
    section_tone: str = "blue",
    theme_id: str = "mofe_body",
    logo_pos: str = "bottom_center",
    concept_style_block: str = "",
) -> str:
    bullets = slide.get("bullets") or []
    blines = "\n".join(f"- {b}" for b in bullets) if bullets else ("(no bullets)" if copy_locale == "en" else "(불릿 없음)")
    foot = slide.get("footnote") or ("(no footnote)" if copy_locale == "en" else "(각주 없음)")
    role = slide.get("role", "body")
    priority = (
        f"[최우선 — 페이지 {page_index_1based} 반드시 반영할 문안]\n"
        f"역할: {role}\n"
        f"시리즈명(참고): {plan.get('series_title', '')}\n"
        f"헤드카피(참고): {plan.get('head_copy', '')}\n"
        f"슬라이드 제목: {slide.get('title', '')}\n"
        f"불릿:\n{blines}\n"
        f"각주: {foot}\n"
    )
    if copy_locale == "en":
        tail = (
            "\n[작업 지시]\n"
            "Create ONE finished policy card-news inner or closing page. "
            "Follow the full [본문 디자인 규격] below for canvas, palette, typography, header, capsules, margins, 3D illustration areas, etc. "
            "The spec may be in Korean; use it as strict visual/layout rules. "
            "Place all copy from [최우선] clearly in natural English. "
            "Draw the government logo per [ENGLISH IMAGE — AI-DRAWN LOGO]. Single finished image."
            + build_english_logo_layout_block(logo_pos, theme_id)
        )
    else:
        tail = (
            "\n[작업 지시]\n"
            "재정경제부 카드뉴스 본문(또는 맺음) 페이지 1장을 생성한다. "
            "[본문 디자인 규격]의 캔버스·색체·타이포·헤더·캡슐·여백·3D 일러스트·정부 로고를 반영하고, "
            "위 [최우선] 문안을 한글로 선명하게 배치한다. 단일 완성 이미지."
            + build_korean_logo_layout_block(logo_pos, theme_id)
        )
    tone_block = build_section_tone_prompt_block(
        section_tone, theme_id, for_cover=False, copy_locale=copy_locale
    )
    spec = _clip_middle(
        body_template_full,
        PROMPT_MAX_CHARS - len(priority) - len(tone_block) - len(theme_desc) - len(tail) - 80,
    )
    concept_part = f"\n\n{concept_style_block.strip()}\n" if concept_style_block.strip() else ""
    body = _clip_middle(
        f"{priority}\n\n{tone_block}{concept_part}\n\n[본문 디자인 규격 — 아래 전문을 모두 반영]\n{spec}\n\n"
        f"[현재 디자인 설정]\n{theme_desc}{tail}",
        PROMPT_MAX_CHARS + 2000,
    )
    return append_image_safety(body)


def generate_image_png_bytes(client: OpenAI, model: str, prompt: str) -> bytes | None:
    """Images API로 PNG 바이트 생성 (프롬프트는 호출부에서 완성)."""
    p = prompt[:31000]
    base_kw: dict[str, Any] = {
        "model": model,
        "prompt": p,
        "n": 1,
        "output_format": "png",
        "moderation": "auto",
        "size": "1024x1024",
        "quality": "medium",
    }
    if model.startswith("gpt-image-2"):
        try:
            resp = client.images.generate(**base_kw)
        except Exception as exc:
            logger.warning("Image API error (%s): %s", model, exc)
            try:
                resp = client.images.generate(
                    model=model,
                    prompt=p,
                    n=1,
                    size="auto",
                    quality="auto",
                    output_format="png",
                    moderation="auto",
                )
            except Exception as exc2:
                logger.warning("Image API retry failed (%s): %s", model, exc2)
                return None
    else:
        try:
            resp = client.images.generate(**base_kw)
        except Exception as exc:
            logger.warning("Image API error (%s): %s", model, exc)
            return None
    return _decode_response(resp)


def generate_plan_card_jpegs(
    client: OpenAI,
    model: str,
    plan_dict: dict[str, Any],
    *,
    theme_desc: str,
    out_dir: Path,
    cover_template_full: str,
    body_template_full: str,
    progress_callback: Any | None = None,
    jpeg_size: tuple[int, int] = (800, 1000),
    quality: int = 92,
    copy_locale: str = "ko",
    section_tone: str = "blue",
    theme_id: str = "mofe_body",
    logo_pos: str = "bottom_center",
    concept_style_block: str = "",
) -> list[Path]:
    """슬라이드별 전면 카드 이미지를 생성해 JPEG로 저장한다."""
    from io import BytesIO

    from PIL import Image

    if not cover_template_full:
        cover_template_full = load_cover_template_text()
    if not body_template_full:
        body_template_full = load_body_template_text()

    assert_plan_safe(plan_dict)
    out_dir.mkdir(parents=True, exist_ok=True)
    slides = plan_dict.get("slides") or []
    paths: list[Path] = []
    total = len(slides)
    for i, slide in enumerate(slides):
        if i == 0:
            prompt = build_first_card_image_prompt(
                plan_dict,
                slide,
                cover_template_full=cover_template_full,
                theme_desc=theme_desc,
                copy_locale=copy_locale,
                section_tone=section_tone,
                theme_id=theme_id,
                logo_pos=logo_pos,
                concept_style_block=concept_style_block,
            )
        else:
            prompt = build_body_card_image_prompt(
                plan_dict,
                slide,
                i + 1,
                body_template_full=body_template_full,
                theme_desc=theme_desc,
                copy_locale=copy_locale,
                section_tone=section_tone,
                theme_id=theme_id,
                logo_pos=logo_pos,
                concept_style_block=concept_style_block,
            )
        png_bytes = generate_image_png_bytes(client, model, prompt)
        if not png_bytes:
            raise RuntimeError(f"페이지 {i + 1} 이미지 생성 실패 (모델: {model})")
        im = Image.open(BytesIO(png_bytes)).convert("RGB")
        im = im.resize(jpeg_size, Image.Resampling.LANCZOS)
        role = slide.get("role", "body")
        fname = f"{i + 1:02d}_{role}.jpg"
        p = out_dir / fname
        im.save(p, format="JPEG", quality=quality, optimize=True)
        paths.append(p)
        if progress_callback is not None:
            progress_callback(i + 1, total)
    return paths
