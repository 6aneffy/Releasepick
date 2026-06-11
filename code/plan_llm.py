"""Generate structured card news plan from press release text via OpenAI."""

from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI

from content_filter import (
    PLAN_EDITOR_SAFETY_RULES,
    ContentFilterError,
    FilterIssue,
    assert_plan_safe,
    format_issues_for_revision,
    run_plan_generation_filter,
    scan_text,
)
from models import CardNewsPlan
from template_catalog import load_one_page_template_text
from template_resources import load_body_template_text, load_cover_template_text

MAX_PLAN_SAFETY_RETRIES = 2

JSON_SCHEMA_BLOCK = """다음 JSON 스키마에 맞게만 응답하세요. 다른 설명 텍스트는 금지입니다.

스키마:
{
  "series_title": "시리즈 한 줄 제목",
  "head_copy": "임팩트 있는 헤드카피 (짧게)",
  "slides": [
    {
      "role": "cover" | "body" | "closing",
      "title": "슬라이드 제목",
      "bullets": ["불릿1", "불릿2"],
      "footnote": "선택, 출처나 각주"
    }
  ]
}

규칙:
- slides 개수는 사용자가 요청한 target_pages와 정확히 일치해야 합니다.
- target_pages가 1이면 슬라이드 1장만 두며 role은 \"cover\" (표지 1장)로 한다.
- target_pages가 2이면 첫 장 \"cover\", 둘째 장 \"closing\".
- target_pages가 3 이상이면 첫 장은 반드시 \"cover\", 마지막은 \"closing\", 그 사이는 \"body\".
- cover: bullets는 비우거나 핵심 한 줄만. closing: bullets는 짧은 요약 또는 비움 가능.
- 본문(body) 슬라이드는 불릿 3~5개 권장, 한 불릿은 80자 이내로.
- 사실 왜곡 없이 입력 문서 내용만 요약·재배열합니다.
- 첫 슬라이드(cover) 문안·톤·정보 위계는 시스템에 제공된 [표지 템플릿] 전문의 규칙을 모두 따른다.
- 둘째 슬라이드부터 마지막까지는 [본문 템플릿] 전문의 규칙(캔버스, 색, 타이포, 레이아웃 패턴)을 모두 따른다.
""" + PLAN_EDITOR_SAFETY_RULES


def _clip_template_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars // 2] + "\n...[생략]...\n" + text[-max_chars // 2 :]


def _json_schema_block(target_pages: int) -> str:
    if target_pages != 1:
        return JSON_SCHEMA_BLOCK
    return (
        JSON_SCHEMA_BLOCK.replace(
            "첫 슬라이드(cover) 문안·톤·정보 위계는 시스템에 제공된 [표지 템플릿] 전문의 규칙을 모두 따른다.",
            "1장 카드뉴스는 시스템에 제공된 [1장 포스터형 템플릿] 전문만 따른다. "
            "표지·본문 템플릿은 적용하지 않는다.",
        ).replace(
            "둘째 슬라이드부터 마지막까지는 [본문 템플릿] 전문의 규칙(캔버스, 색, 타이포, 레이아웃 패턴)을 모두 따른다.",
            "1장 제작이므로 본문·맺음 슬라이드는 작성하지 않는다.",
        )
    )


def _build_system_prompt(*, target_pages: int = 2, max_template_chars: int = 45000) -> str:
    base = (
        "당신은 대한민국 공공기관 보도자료를 카드뉴스용으로 재구성하는 편집자입니다.\n"
        "입력은 보도자료 전문(한국어)입니다.\n\n"
        + _json_schema_block(target_pages)
    )
    if target_pages == 1:
        one_page = _clip_template_text(
            load_one_page_template_text(), max_template_chars
        )
        return (
            base
            + "\n\n=== [1장 포스터형 템플릿] 전문 (유일한 디자인·문안 규격) ===\n"
            + one_page
        )
    cover = _clip_template_text(load_cover_template_text(), max_template_chars)
    body = _clip_template_text(load_body_template_text(), max_template_chars)
    return (
        base
        + "\n\n=== [표지 템플릿] 전문 (첫 페이지 기획 시 전부 반영) ===\n"
        + cover
        + "\n\n=== [본문 템플릿] 전문 (2페이지째 이후 기획 시 전부 반영) ===\n"
        + body
    )


def _repair_slides(raw: dict[str, Any], target_pages: int) -> list[dict[str, Any]]:
    slides = raw.get("slides") or []
    out: list[dict[str, Any]] = []
    for s in slides:
        if len(out) >= target_pages:
            break
        if not isinstance(s, dict):
            continue
        out.append(
            {
                "role": str(s.get("role", "body")).lower(),
                "title": str(s.get("title", ""))[:500],
                "bullets": s.get("bullets") if isinstance(s.get("bullets"), list) else [],
                "footnote": s.get("footnote"),
            }
        )
    while len(out) < target_pages:
        idx = len(out)
        if idx == 0:
            out.append({"role": "cover", "title": raw.get("series_title", "표지"), "bullets": [], "footnote": None})
        elif idx == target_pages - 1:
            out.append({"role": "closing", "title": "맺음말", "bullets": [], "footnote": None})
        else:
            out.append({"role": "body", "title": f"본문 {idx}", "bullets": ["내용을 입력하세요."], "footnote": None})
    out = out[:target_pages]
    for i in range(len(out)):
        if i == 0:
            out[i]["role"] = "cover"
        elif i == len(out) - 1:
            out[i]["role"] = "closing"
        else:
            out[i]["role"] = "body"
    return out


def _normalize_plan_raw(raw: dict[str, Any], target_pages: int) -> dict[str, Any]:
    raw = dict(raw)
    raw["slides"] = _repair_slides(raw, target_pages)
    if not raw.get("series_title"):
        raw["series_title"] = "정책 안내"
    if not raw.get("head_copy"):
        raw["head_copy"] = str(raw["series_title"])[:80]
    return raw


def _build_plan_user_message(
    press_text: str,
    target_pages: int,
    *,
    concept_style_block: str | None = None,
) -> str:
    press_issues = scan_text(press_text[:120_000], field="보도자료")
    press_note = ""
    if press_issues:
        press_note = (
            "\n[보도자료 정서 안전] 원문에 민감·논란 소재가 있을 수 있습니다. "
            "기획 JSON에는 일본·북한·식민지·이념·갈등·혐오 표현을 넣지 말고, "
            "대한민국 정책 홍보에 맞는 중립 문안만 작성하세요.\n"
        )
    concept_part = ""
    if concept_style_block and concept_style_block.strip():
        concept_part = f"\n=== [사용자 선택 디자인 컨셉] ===\n{concept_style_block.strip()}\n"
    template_rules = (
        "2) 1장 카드뉴스는 [1장 포스터형 템플릿] 전문만 따른다. "
        "표지·본문 템플릿은 사용하지 않는다.\n"
        if target_pages == 1
        else (
            "2) 첫 페이지(cover)는 [표지 템플릿] 전문의 구조·문체·요소를 모두 반영.\n"
            "3) 둘째 페이지부터 마지막 페이지는 [본문 템플릿] 전문의 규칙을 모두 반영하고, "
            "앱에서 선택한 테마·톤은 이후 단계에서 적용되므로 여기서는 문안 구조만 템플릿에 맞춘다.\n"
        )
    )
    concept_rule = (
        "3) [사용자 선택 디자인 컨셉]이 있으면 문안 톤·정보 위계·강조 요소에 반영한다.\n"
        if target_pages == 1
        else "4) [사용자 선택 디자인 컨셉]이 있으면 문안 톤·정보 위계·강조 요소에 반영한다.\n"
    )
    return (
        "우선순위:\n"
        "1) 보도자료 사실만 사용, 왜곡 금지.\n"
        "1-1) 일본·북한 연상, 일제강점기·식민지 잔재, 보수·진보 등 정치 이념 갈등, 젠더·세대·지역 갈등, 혐오·비하 표현은 기획 문안에 넣지 않는다.\n"
        f"{template_rules}"
        f"{concept_rule}"
        f"{press_note}"
        f"{concept_part}\n"
        f"target_pages={target_pages}\n"
        "(페이지가 1이면 표지 슬라이드만, 2면 표지+맺음말만 작성.)\n\n"
        "=== 보도자료 ===\n"
        f"{press_text[:120_000]}"
    )


def _call_plan_json(
    client: OpenAI,
    messages: list[dict[str, str]],
    *,
    model: str,
) -> dict[str, Any]:
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0.4,
    )
    content = resp.choices[0].message.content or "{}"
    raw = json.loads(content)
    return raw if isinstance(raw, dict) else {}


def generate_plan(
    client: OpenAI,
    press_text: str,
    *,
    target_pages: int,
    model: str = "gpt-4o-mini",
    concept_style_block: str | None = None,
) -> CardNewsPlan:
    """기획 LLM 호출 후 정서·이미지 안전 필터를 적용(위반 시 자동 수정 재시도).

    concept_style_block: 2단계에서 선택한 디자인 컨셉 설명(기획 프롬프트에 주입).
    """
    if target_pages < 1:
        target_pages = 1
    system = _build_system_prompt(target_pages=target_pages)
    user = _build_plan_user_message(
        press_text, target_pages, concept_style_block=concept_style_block
    )
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    plan_dict: dict[str, Any] | None = None
    issues: list[FilterIssue] = []

    for attempt in range(MAX_PLAN_SAFETY_RETRIES + 1):
        if attempt == 0:
            raw = _call_plan_json(client, messages, model=model)
        else:
            revise_msg = (
                "이전에 출력한 기획 JSON에 정서·이미지 안전 필터 위반이 있습니다. "
                "slides 개수와 각 slide의 role(cover/body/closing)은 그대로 두고, "
                "아래 위반 항목만 중립적인 정책 홍보 문안으로 고친 JSON 객체 하나만 다시 출력하세요.\n\n"
                + format_issues_for_revision(issues)
            )
            revision_messages = [
                *messages,
                {"role": "assistant", "content": json.dumps(plan_dict, ensure_ascii=False)},
                {"role": "user", "content": revise_msg},
            ]
            raw = _call_plan_json(client, revision_messages, model=model)

        plan_dict = _normalize_plan_raw(raw, target_pages)
        issues = run_plan_generation_filter(plan_dict)
        if not issues:
            return CardNewsPlan.model_validate(plan_dict)

    raise ContentFilterError(issues)


def translate_plan_to_english(
    client: OpenAI,
    plan_dict: dict[str, Any],
    *,
    model: str = "gpt-4o-mini",
) -> dict[str, Any]:
    """한국어 기획안을 동일 구조의 영어 기획으로 번역한다 (이미지 프롬프트용)."""
    src = CardNewsPlan.model_validate(plan_dict)
    payload = src.model_dump(mode="json")
    user_json = json.dumps(payload, ensure_ascii=False)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You translate Korean card-news plan JSON into natural English for publication. "
                    "Output ONLY a JSON object with the exact same structure: "
                    "series_title, head_copy, slides (same length as input). "
                    "Each slide: keep role unchanged (cover/body/closing), translate title, bullets, footnote to English. "
                    "footnote may be null. Do not add or remove slides or keys. "
                    "Never introduce Japan/North Korea cultural or political imagery terms; "
                    "no political ideology camps, gender/generational/regional conflict, or hate speech; "
                    "keep neutral Korean government policy tone."
                ),
            },
            {"role": "user", "content": user_json},
        ],
        response_format={"type": "json_object"},
        temperature=0.25,
    )
    content = resp.choices[0].message.content or "{}"
    raw = json.loads(content)
    if not isinstance(raw, dict):
        raw = {}
    n = len(src.slides)
    raw["slides"] = _repair_slides(raw, n)
    orig_slides = src.model_dump(mode="json").get("slides") or []
    for i, s in enumerate(raw.get("slides") or []):
        if i < len(orig_slides) and isinstance(s, dict):
            s["role"] = orig_slides[i].get("role", s.get("role", "body"))
    if not raw.get("series_title"):
        raw["series_title"] = str(payload.get("series_title", ""))
    if not raw.get("head_copy"):
        raw["head_copy"] = str(payload.get("head_copy", ""))
    out = CardNewsPlan.model_validate(raw).model_dump(mode="json")
    assert_plan_safe(out)
    return out


def parse_plan_json(text: str) -> CardNewsPlan:
    """Parse user-edited JSON from text area; tolerate markdown fences."""
    t = text.strip()
    fence = re.match(r"^```(?:json)?\s*\n(.*)\n```\s*$", t, re.DOTALL)
    if fence:
        t = fence.group(1).strip()
    data = json.loads(t)
    if not isinstance(data, dict):
        raise ValueError("루트는 JSON 객체여야 합니다.")
    slides = data.get("slides") or []
    n = max(1, len(slides))
    data["slides"] = _repair_slides(data, n)
    plan = CardNewsPlan.model_validate(data)
    assert_plan_safe(plan.to_json_dict())
    return plan
