"""
릴리즈픽 — 카드뉴스 제작 (Streamlit MVP)
"""

from __future__ import annotations

import json
import os
import tempfile
import traceback
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

import job_store
from buffer_publish import BufferError, create_instagram_post
from caption_llm import (
    DEFAULT_CAPTION_SYSTEM_PROMPT,
    MAX_CAPTION_LEN,
    generate_instagram_caption,
)
from content_filter import ContentFilterError, assert_plan_safe, scan_plan_dict
from export_plan_pptx import build_plan_pptx_bytes
from image_gen import (
    ENGLISH_LOGO_WORDMARK,
    build_theme_description,
    generate_plan_card_jpegs,
    image_models_for_selectbox,
    resolve_model,
)
from models import CardNewsPlan
from package_export import build_export_zip_bytes
from pdf_extract import extract_text_from_pdf_bytes
from plan_llm import generate_plan, translate_plan_to_english
from render_cards import list_theme_ids
from supabase_storage import (
    SupabaseStorageError,
    UploadedAsset,
    delete_objects,
    upload_card_images,
)
from template_catalog import page_group
from template_resources import (
    DEFAULT_MULTIPAGE_VARIANT,
    load_body_template_text,
    load_cover_template_text,
    multipage_variant_labels,
)

CODE_DIR = Path(__file__).resolve().parent
ROOT = CODE_DIR.parent
_ENV = ROOT / ".env"
load_dotenv(dotenv_path=_ENV, override=False)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "").strip()
BUFFER_API_KEY = os.getenv("BUFFER_API_KEY", "").strip()
BUFFER_CHANNEL_ID = os.getenv("BUFFER_CHANNEL_ID", "").strip()
BUFFER_ORGANIZATION_ID = os.getenv("BUFFER_ORGANIZATION_ID", "").strip()
_SNS_READY = bool(
    SUPABASE_URL
    and SUPABASE_SERVICE_ROLE_KEY
    and SUPABASE_BUCKET
    and BUFFER_API_KEY
    and BUFFER_CHANNEL_ID
)


def _init_session() -> None:
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    defaults = {
        "pdf_bytes": None,
        "pdf_name": "",
        "press_text": "",
        "plan_text": "",
        "plan_dict": None,
        "plan_phase": "draft",
        "plan_revisions_remaining": 0,
        "plan_first_approved": False,
        "plan_bump": 0,
        "card_paths": [],
        "card_paths_en": [],
        "card_review_approved": False,
        "card_revisions_remaining": 0,
        "logo_bytes": None,
        "character_bytes": None,
        "target_pages_group": None,
        "multipage_variant": DEFAULT_MULTIPAGE_VARIANT,
        "instagram_caption": "",
        "instagram_uploaded_post_id": None,
        "instagram_uploaded_keys": [],
        "instagram_cleanup_done": False,
        "_hydrated": False,
        "_seed_bump": -1,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


def _snapshot() -> dict:
    return {
        "plan_text": st.session_state.get("plan_text", ""),
        "plan_dict": st.session_state.get("plan_dict"),
        "plan_phase": st.session_state.get("plan_phase", "draft"),
        "plan_revisions_remaining": st.session_state.get("plan_revisions_remaining", 0),
        "plan_first_approved": st.session_state.get("plan_first_approved", False),
        "plan_bump": st.session_state.get("plan_bump", 0),
        "card_review_approved": st.session_state.get("card_review_approved", False),
        "card_revisions_remaining": st.session_state.get("card_revisions_remaining", 0),
        "card_paths": st.session_state.get("card_paths", []),
        "card_paths_en": st.session_state.get("card_paths_en", []),
        "press_text": st.session_state.get("press_text", ""),
        "pdf_name": st.session_state.get("pdf_name", ""),
        "multipage_variant": st.session_state.get("multipage_variant", DEFAULT_MULTIPAGE_VARIANT),
        "instagram_caption": st.session_state.get("instagram_caption", ""),
        "instagram_uploaded_post_id": st.session_state.get("instagram_uploaded_post_id"),
        "instagram_uploaded_keys": st.session_state.get("instagram_uploaded_keys", []),
        "instagram_cleanup_done": st.session_state.get("instagram_cleanup_done", False),
    }


_ERROR_LOG = CODE_DIR / "_last_error.log"


def _log_error(context: str, tb: str) -> None:
    """트레이스백을 파일에 안전하게 기록 (stdout 미사용 — Streamlit 환경에서 print는 OSError 발생 가능)."""
    try:
        with _ERROR_LOG.open("a", encoding="utf-8") as f:
            f.write(f"\n=== {context} @ {datetime.now().isoformat()} ===\n{tb}\n")
    except OSError:
        pass


def _resolve_design_templates(
    target_pages: int, multipage_variant: str
) -> tuple[str, str, bool]:
    """카드 이미지용 디자인 규격 로드.

    1장이면 themes/template1/템플릿-1.txt만, 2장 이상이면 선택한 변형(v1/v2)의 표지·본문.
    반환: (cover_full, body_full, single_page).
    """
    if target_pages == 1:
        from template_catalog import load_one_page_template_text

        return load_one_page_template_text(), "", True
    return (
        load_cover_template_text(multipage_variant),
        load_body_template_text(multipage_variant),
        False,
    )


def _persist() -> None:
    job_store.save_snapshot(st.session_state.session_id, _snapshot())


def _try_hydrate() -> None:
    if st.session_state.get("_hydrated"):
        return
    job_store.init_db()
    snap = job_store.load_snapshot(st.session_state.session_id)
    if snap:
        for k, v in snap.items():
            if k in ("plan_dict",) and v is None:
                continue
            st.session_state[k] = v
        if st.session_state.get("plan_dict") and not st.session_state.get("plan_text"):
            st.session_state.plan_text = json.dumps(
                st.session_state.plan_dict, ensure_ascii=False, indent=2
            )
        st.session_state._seed_bump = -1
    st.session_state._hydrated = True


def _plan_to_text() -> None:
    if st.session_state.plan_dict:
        st.session_state.plan_text = json.dumps(
            st.session_state.plan_dict, ensure_ascii=False, indent=2
        )


def _seed_page_widgets_from_plan() -> None:
    pd = st.session_state.plan_dict
    if not pd:
        return
    st.session_state.pg_series = pd.get("series_title", "")
    st.session_state.pg_head = pd.get("head_copy", "")
    for i, s in enumerate(pd.get("slides") or []):
        st.session_state[f"pg_{i}_title"] = s.get("title", "")
        st.session_state[f"pg_{i}_bullets"] = "\n".join(s.get("bullets") or [])
        st.session_state[f"pg_{i}_footnote"] = (s.get("footnote") or "") or ""


def _guard_plan(plan_d: dict | None, *, context: str) -> bool:
    """기획안 안전 검사. 실패 시 Streamlit 오류 표시 후 False."""
    if not plan_d:
        return False
    try:
        assert_plan_safe(plan_d)
    except ContentFilterError as exc:
        st.error(f"**{context}** — 정서·이미지 안전 필터\n\n{exc}")
        return False
    return True


def _widgets_into_plan_dict() -> None:
    pd = st.session_state.plan_dict
    if not pd or "pg_series" not in st.session_state:
        return
    pd["series_title"] = str(st.session_state.get("pg_series", ""))
    pd["head_copy"] = str(st.session_state.get("pg_head", ""))
    for i, s in enumerate(pd.get("slides") or []):
        s["title"] = str(st.session_state.get(f"pg_{i}_title", ""))
        bl = st.session_state.get(f"pg_{i}_bullets", "")
        s["bullets"] = [ln.strip() for ln in str(bl).splitlines() if ln.strip()]
        fn = str(st.session_state.get(f"pg_{i}_footnote", "")).strip()
        s["footnote"] = fn or None
    _plan_to_text()


def main() -> None:
    st.set_page_config(page_title="릴리즈픽", page_icon="🪪", layout="wide")
    _init_session()
    _try_hydrate()

    st.title("릴리즈픽")
    if not OPENAI_API_KEY:
        st.error("`.env`에 `OPENAI_API_KEY`를 설정하세요. (저장소 루트 `Releasepick/.env`)")
        st.stop()

    client = OpenAI(api_key=OPENAI_API_KEY)

    with st.sidebar:
        if st.button("세션 초기화 (로컬)"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    badge_cols = st.columns(4)
    with badge_cols[0]:
        st.caption(f"세션: `{st.session_state.session_id[:8]}…`")
    with badge_cols[1]:
        if st.session_state.plan_phase == "post_first":
            st.metric("남은 기획 수정", st.session_state.plan_revisions_remaining)
    with badge_cols[2]:
        if st.session_state.card_review_approved:
            st.metric("남은 카드 재생성", st.session_state.card_revisions_remaining)
    with badge_cols[3]:
        st.caption(f"기획 단계: **{st.session_state.plan_phase}**")

    st.divider()
    st.subheader("1. 보도자료 PDF")
    up = st.file_uploader("PDF 업로드", type=["pdf"])
    if up:
        st.session_state.pdf_bytes = up.getvalue()
        st.session_state.pdf_name = up.name

    if st.session_state.pdf_bytes:
        st.caption(f"파일: {st.session_state.pdf_name}")

    target_pages = st.slider("페이지 수(슬라이드)", 1, 12, 5, key="target_pages_slider")
    pg_group = page_group(target_pages)
    if st.session_state.get("target_pages_group") != pg_group:
        st.session_state.target_pages_group = pg_group

    if target_pages == 1:
        st.caption("1장 제작 — `themes/template1/템플릿-1.txt` 포스터형 템플릿이 적용됩니다.")
        multipage_variant = DEFAULT_MULTIPAGE_VARIANT
    else:
        _variant_labels = multipage_variant_labels()
        _variant_ids = list(_variant_labels.keys())
        _cur_variant = st.session_state.get("multipage_variant", DEFAULT_MULTIPAGE_VARIANT)
        multipage_variant = st.radio(
            "디자인 템플릿 (2장 이상)",
            _variant_ids,
            index=_variant_ids.index(_cur_variant) if _cur_variant in _variant_ids else 0,
            format_func=lambda v: _variant_labels.get(v, v),
            horizontal=True,
            key="multipage_variant",
        )
        st.caption(
            "선택한 템플릿(표지·본문)이 **기획안과 카드 생성**에 모두 적용됩니다. "
            "변경 시 기획을 다시 생성하세요."
        )

    if st.button("PDF에서 텍스트 추출", disabled=not st.session_state.pdf_bytes):
        with st.spinner("추출 중…"):
            st.session_state.press_text = extract_text_from_pdf_bytes(st.session_state.pdf_bytes)
        if not st.session_state.press_text.strip():
            st.warning("추출된 텍스트가 없습니다. 스캔 PDF일 수 있습니다.")
        else:
            st.success(f"추출 완료 ({len(st.session_state.press_text)}자)")
        _persist()

    if st.session_state.press_text:
        with st.expander("추출 텍스트 미리보기"):
            st.text(st.session_state.press_text[:8000])

    st.divider()
    st.subheader("2. 기획안 (LLM)")
    if st.button(
        "기획 생성",
        disabled=not st.session_state.press_text.strip(),
    ):
        try:
            with st.spinner(
                "① LLM 기획 작성 → ② 정서·이미지 안전 필터 검사 "
                "(위반 시 자동 수정, 최대 2회)…"
            ):
                plan = generate_plan(
                    client,
                    st.session_state.press_text,
                    target_pages=target_pages,
                    template_variant=multipage_variant,
                )
                st.session_state.plan_dict = plan.to_json_dict()
                st.session_state.plan_phase = "draft"
                st.session_state.plan_first_approved = False
                st.session_state.plan_revisions_remaining = 0
                st.session_state.plan_bump = st.session_state.get("plan_bump", 0) + 1
                st.session_state._seed_bump = -1
                _plan_to_text()
            st.success("기획안이 생성되었습니다. (정서 안전 필터 통과)")
            _persist()
            st.rerun()
        except ContentFilterError as exc:
            st.error(str(exc))
            st.stop()

    plan_locked = st.session_state.plan_phase == "locked"
    plan_readonly = plan_locked or (
        st.session_state.plan_phase == "post_first" and st.session_state.plan_revisions_remaining <= 0
    )

    if st.session_state.plan_dict:
        bump = st.session_state.get("plan_bump", 0)
        if st.session_state.get("_seed_bump", -1) != bump:
            _seed_page_widgets_from_plan()
            st.session_state._seed_bump = bump

        st.markdown("##### 페이지별 내용 (네모 박스에서 수정)")
        with st.container(border=True):
            st.caption("공통 문안")
            st.text_input("시리즈명", key="pg_series", disabled=plan_readonly)
            st.text_input("헤드카피", key="pg_head", disabled=plan_readonly)

        slides = st.session_state.plan_dict.get("slides") or []
        role_ko = {"cover": "표지", "body": "본문", "closing": "맺음"}
        for i, slide in enumerate(slides):
            r = slide.get("role", "body")
            with st.container(border=True):
                st.markdown(f"**페이지 {i + 1}** · {role_ko.get(str(r), r)}")
                st.text_input("슬라이드 제목", key=f"pg_{i}_title", disabled=plan_readonly)
                st.text_area(
                    "불릿 (줄마다 하나)",
                    key=f"pg_{i}_bullets",
                    height=120,
                    disabled=plan_readonly,
                )
                st.text_input("각주 (선택)", key=f"pg_{i}_footnote", disabled=plan_readonly)

        if st.button("페이지 편집 내용을 기획안에 반영", disabled=plan_readonly):
            _widgets_into_plan_dict()
            if not _guard_plan(st.session_state.plan_dict, context="기획 반영"):
                st.stop()
            _persist()
            st.success("기획안이 업데이트되었습니다.")

        with st.expander("고급: JSON 보기"):
            st.code(st.session_state.get("plan_text", "") or "", language="json")

        plan_issues = scan_plan_dict(st.session_state.plan_dict)
        if plan_issues:
            st.warning(
                f"정서 안전: 현재 기획에 검토가 필요한 표현 {len(plan_issues)}건이 있습니다. "
                "카드 생성 전에 수정하세요."
            )
        else:
            st.caption("정서·이미지 안전 필터: 현재 기획 문안 검사 통과")

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("기획 1차 승인", disabled=st.session_state.plan_dict is None or st.session_state.plan_phase != "draft"):
            _widgets_into_plan_dict()
            if not _guard_plan(st.session_state.plan_dict, context="기획 1차 승인"):
                st.stop()
            st.session_state.plan_phase = "post_first"
            st.session_state.plan_revisions_remaining = 2
            st.session_state.plan_first_approved = True
            _persist()
            st.rerun()
    with c2:
        if st.button(
            "수정 반영 (기획)",
            disabled=st.session_state.plan_phase != "post_first"
            or st.session_state.plan_revisions_remaining <= 0
            or plan_locked,
        ):
            _widgets_into_plan_dict()
            st.session_state.plan_revisions_remaining -= 1
            _persist()
            st.rerun()
    with c3:
        if st.button(
            "기획 확정 → 카드 생성 단계로",
            disabled=st.session_state.plan_dict is None
            or st.session_state.plan_phase == "draft"
            or plan_locked,
        ):
            _widgets_into_plan_dict()
            if not _guard_plan(st.session_state.plan_dict, context="기획 확정"):
                st.stop()
            st.session_state.plan_phase = "locked"
            _persist()
            st.rerun()

    st.divider()
    st.subheader("3. 디자인 · 이미지 모델")
    if target_pages == 1:
        st.caption(
            "1장 제작 — `themes/template1/템플릿-1.txt` 포스터형 템플릿이 카드 생성에 적용됩니다."
        )
    else:
        st.caption(
            f"선택한 템플릿: **{multipage_variant_labels().get(multipage_variant, multipage_variant)}** "
            "— 위 '페이지 수' 아래에서 변경할 수 있으며, 카드 생성 시 GPT Image 프롬프트에 포함됩니다."
        )
    dc1, dc2 = st.columns(2)
    with dc1:
        themes = list_theme_ids()
        theme_id = st.selectbox("템플릿 (YAML)", themes, index=0, key="dc_theme")
        section_tone = st.selectbox(
            "섹션 컬러 톤",
            ["neutral", "green", "blue", "purple", "orange"],
            index=2,
            format_func=lambda x: {
                "neutral": "기본(블루 띠)",
                "green": "녹색",
                "blue": "파랑",
                "purple": "보라",
                "orange": "주황",
            }.get(x, x),
            key="dc_tone",
        )
        body_layout_label = st.radio(
            "본문 레이아웃",
            ["여백형 (패턴 A)", "흰 카드형 (패턴 B)"],
            horizontal=True,
            key="dc_layout",
        )
        body_layout = "simple" if "A" in body_layout_label else "white_card"
        font_scale = st.slider("폰트 크기 배율 (레이아웃 참고)", 0.75, 1.25, 1.0, 0.05, key="dc_fscale")
    with dc2:
        title_color = st.color_picker("제목 색 (지정 시)", value="#111111", key="dc_tcol")
        body_color = st.color_picker("본문 색 (지정 시)", value="#333333", key="dc_bcol")
        use_custom_title = st.checkbox("제목 색 반영", value=False, key="dc_ut")
        use_custom_body = st.checkbox("본문 색 반영", value=False, key="dc_ub")
        logo_pos = st.radio(
            "로고 위치",
            ["top_right", "top_left", "bottom_center"],
            horizontal=True,
            key="dc_logo",
        )
        char_file = st.file_uploader("캐릭터 PNG (선택, 전면 AI 생성 시 미사용)", type=["png"], key="dc_char")
        if char_file:
            st.session_state.character_bytes = char_file.getvalue()
        p_logo = ROOT / "logo.png"
        if p_logo.exists():
            st.caption(
                f"로고는 **AI가 카드 이미지 안에 직접** 그립니다. 한글: 「재정경제부」 / "
                f"영문: 「{ENGLISH_LOGO_WORDMARK}」(스타일 참고: `{p_logo.name}`)"
            )

    img_model_label = st.selectbox(
        "이미지 생성 모델 (카드 전면)",
        image_models_for_selectbox(),
        index=0,
        help="카드 생성 클릭 시 프롬프트는 표시하지 않고 곧바로 API 요청합니다.",
        key="dc_imgmodel",
    )
    img_model = resolve_model(img_model_label)

    theme_desc = build_theme_description(
        theme_id=theme_id,
        section_tone=section_tone,
        body_layout=body_layout,
        font_scale=font_scale,
        use_custom_title=use_custom_title,
        use_custom_body=use_custom_body,
        title_color=title_color,
        body_color=body_color,
        logo_pos=logo_pos,
    )
    eff_title_color = title_color if use_custom_title else None
    eff_body_color = body_color if use_custom_body else None
    st.divider()
    st.subheader("4. 카드 이미지 (JPEG)")
    out_root = Path(tempfile.gettempdir()) / "cardnews_exports" / st.session_state.session_id
    out_root.mkdir(parents=True, exist_ok=True)

    st.caption(
        "카드 생성 시 동일 템플릿·디자인 설정으로 **한국어 세트**를 만든 뒤 기획을 번역해 **영어 세트**를 추가 생성합니다. "
        "(API 호출이 페이지 수의 약 2배입니다.) "
        "**한·영 세트** 모두 GPT Image가 **같은 스타일의 정부 로고**를 그리며, 영문만 **"
        f"{ENGLISH_LOGO_WORDMARK}** 문구로 표시합니다(선택한 **로고 위치** 반영). "
        "일본·북한·식민지 잔재, 정치 이념·갈등(젠더·세대·지역), 혐오 표현은 기획·프롬프트·생성 단계에서 차단됩니다."
    )
    with st.expander("정서·이미지 안전 필터 안내"):
        st.markdown(
            "- **기획(LLM·수동 편집)**: 일본·식민지 잔재, 북한·분단, **보수·진보·좌우 이념**, **젠더·세대·지역 갈등**, **혐오·비하·차별** 표현, 논란 국기 등 자동 검사\n"
            "- **이미지 프롬프트**: 동일 금지 규칙을 모든 GPT Image 요청에 강제 부착\n"
            "- **카드 생성**: 통과하지 않은 기획은 API 호출 없이 중단"
        )

    _gen_phase = st.session_state.plan_phase
    if _gen_phase != "locked":
        st.info(
            f"카드를 생성하려면 먼저 **2. 기획안** 단계에서 기획을 확정해야 합니다. "
            f"(현재 단계: `{_gen_phase}`) → '기획 1차 승인' 후 '기획 확정 → 카드 생성 단계로'를 누르세요."
        )
    if st.button(
        "카드 생성 (첫 렌더)",
        disabled=_gen_phase != "locked" or not st.session_state.plan_dict,
        key="btn_card_render",
    ):
        _widgets_into_plan_dict()
        plan_d = st.session_state.plan_dict
        if not plan_d:
            st.error("기획안이 없습니다.")
            st.stop()
        if not _guard_plan(plan_d, context="카드 생성"):
            st.stop()
        cover_full, body_full, single_page = _resolve_design_templates(
            target_pages, multipage_variant
        )
        if not cover_full.strip() or (not single_page and not body_full.strip()):
            if single_page:
                st.error("템플릿 파일을 찾을 수 없습니다. `Releasepick/themes/template1/템플릿-1.txt` 경로를 확인하세요.")
            else:
                st.error("템플릿 파일을 찾을 수 없습니다. `Releasepick/themes/template2/` 경로를 확인하세요.")
            st.stop()
        prog = st.progress(0)
        try:
            nslides = len(plan_d.get("slides") or [])
            total_steps = max(1, nslides * 2)
            done = [0]

            def _prog_combined(_cur: int, _total: int) -> None:
                done[0] += 1
                prog.progress(min(1.0, done[0] / total_steps))

            ko_dir = out_root / "cards" / "ko"
            en_dir = out_root / "cards" / "en"
            ko_dir.mkdir(parents=True, exist_ok=True)
            en_dir.mkdir(parents=True, exist_ok=True)

            with st.spinner(f"한국어 카드 생성 중… ({img_model}, 페이지당 1~2분 소요)"):
                paths_ko = generate_plan_card_jpegs(
                    client,
                    img_model,
                    plan_d,
                    theme_desc=theme_desc,
                    out_dir=ko_dir,
                    cover_template_full=cover_full,
                    body_template_full=body_full,
                    progress_callback=_prog_combined if nslides else None,
                    copy_locale="ko",
                    section_tone=section_tone,
                    theme_id=theme_id,
                    logo_pos=logo_pos,
                    title_color=eff_title_color,
                    body_color=eff_body_color,
                    single_page_template=single_page,
                )
            st.session_state.card_paths = [str(p) for p in paths_ko]
            st.session_state.card_paths_en = []
            st.session_state.card_review_approved = False
            st.session_state.card_revisions_remaining = 0
            _persist()

            paths_en: list = []
            try:
                with st.spinner(f"영어 번역 → 영어 카드 생성 중… ({img_model})"):
                    plan_en = translate_plan_to_english(client, plan_d)
                    paths_en = generate_plan_card_jpegs(
                        client,
                        img_model,
                        plan_en,
                        theme_desc=theme_desc,
                        out_dir=en_dir,
                        cover_template_full=cover_full,
                        body_template_full=body_full,
                        progress_callback=_prog_combined if nslides else None,
                        copy_locale="en",
                        section_tone=section_tone,
                        theme_id=theme_id,
                        logo_pos=logo_pos,
                        title_color=eff_title_color,
                        body_color=eff_body_color,
                        single_page_template=single_page,
                    )
                st.session_state.card_paths_en = [str(p) for p in paths_en]
                _persist()
            except Exception as exc_en:
                st.warning(
                    f"한국어 카드는 생성되었지만 영어 세트 생성에 실패했습니다: {exc_en}\n\n"
                    "한국어 카드로 계속 진행하거나 '카드 다시 생성'으로 영어 세트를 재시도하세요."
                )

            st.success(
                f"한국어 {len(paths_ko)}장"
                + (f" + 영어 {len(paths_en)}장" if paths_en else " 생성 완료 (영어 세트 제외)")
            )
        except ContentFilterError as exc:
            st.error(str(exc))
        except Exception as exc:
            tb = traceback.format_exc()
            _log_error("카드 생성 실패 (첫 렌더)", tb)
            st.error(f"이미지 생성 실패: {type(exc).__name__}: {exc}")
            st.code(tb)
        finally:
            prog.empty()
        st.rerun()

    if st.session_state.card_paths:
        st.write("**미리보기 (한국어)**")
        cols = st.columns(min(4, len(st.session_state.card_paths)))
        for i, p in enumerate(st.session_state.card_paths):
            if Path(p).exists():
                with cols[i % len(cols)]:
                    st.image(p, use_container_width=True)
        en_paths = st.session_state.get("card_paths_en") or []
        if en_paths:
            st.write("**미리보기 (English)**")
            cols_e = st.columns(min(4, len(en_paths)))
            for i, p in enumerate(en_paths):
                if Path(p).exists():
                    with cols_e[i % len(cols_e)]:
                        st.image(p, use_container_width=True)

    st.divider()
    st.subheader("5. 산출물 검토")
    if st.button(
        "산출물 검토 승인 (재생성 2회 허용)",
        disabled=not st.session_state.card_paths or st.session_state.card_review_approved,
    ):
        st.session_state.card_review_approved = True
        st.session_state.card_revisions_remaining = 2
        _persist()
        st.rerun()

    if st.button(
        "카드 다시 생성",
        disabled=not st.session_state.card_review_approved
        or st.session_state.card_revisions_remaining <= 0
        or not st.session_state.plan_dict,
    ):
        _widgets_into_plan_dict()
        plan_d = st.session_state.plan_dict
        if not plan_d or not _guard_plan(plan_d, context="카드 다시 생성"):
            st.stop()
        cover_full, body_full, single_page = _resolve_design_templates(
            target_pages, multipage_variant
        )
        if not cover_full.strip() or (not single_page and not body_full.strip()):
            st.error("디자인 템플릿 파일을 찾을 수 없습니다.")
            st.stop()
        prog = st.progress(0)
        try:
            nslides = len(plan_d.get("slides") or [])
            total_steps = max(1, nslides * 2)
            done = [0]

            def _prog2(_cur: int, _total: int) -> None:
                done[0] += 1
                prog.progress(min(1.0, done[0] / total_steps))

            ko_dir = out_root / "cards" / "ko"
            en_dir = out_root / "cards" / "en"
            ko_dir.mkdir(parents=True, exist_ok=True)
            en_dir.mkdir(parents=True, exist_ok=True)

            with st.spinner(f"한국어 카드 재생성 중… ({img_model})"):
                paths_ko = generate_plan_card_jpegs(
                    client,
                    img_model,
                    plan_d,
                    theme_desc=theme_desc,
                    out_dir=ko_dir,
                    cover_template_full=cover_full,
                    body_template_full=body_full,
                    progress_callback=_prog2 if nslides else None,
                    copy_locale="ko",
                    section_tone=section_tone,
                    theme_id=theme_id,
                    logo_pos=logo_pos,
                    title_color=eff_title_color,
                    body_color=eff_body_color,
                    single_page_template=single_page,
                )
            st.session_state.card_paths = [str(p) for p in paths_ko]
            st.session_state.card_paths_en = []
            _persist()

            paths_en: list = []
            try:
                with st.spinner(f"영어 번역 → 영어 카드 재생성 중… ({img_model})"):
                    plan_en = translate_plan_to_english(client, plan_d)
                    paths_en = generate_plan_card_jpegs(
                        client,
                        img_model,
                        plan_en,
                        theme_desc=theme_desc,
                        out_dir=en_dir,
                        cover_template_full=cover_full,
                        body_template_full=body_full,
                        progress_callback=_prog2 if nslides else None,
                        copy_locale="en",
                        section_tone=section_tone,
                        theme_id=theme_id,
                        logo_pos=logo_pos,
                        title_color=eff_title_color,
                        body_color=eff_body_color,
                        single_page_template=single_page,
                    )
                st.session_state.card_paths_en = [str(p) for p in paths_en]
            except Exception as exc_en:
                st.warning(f"영어 세트 재생성 실패(한국어는 완료): {exc_en}")
            st.session_state.card_revisions_remaining -= 1
            _persist()
        except ContentFilterError as exc:
            st.error(str(exc))
        except Exception as exc:
            tb = traceback.format_exc()
            _log_error("카드 재생성 실패", tb)
            st.error(f"재생성 실패: {type(exc).__name__}: {exc}")
            st.code(tb)
        finally:
            prog.empty()
        st.rerun()

    st.divider()
    st.subheader("6. 최종 승인 · ZIP 다운로드")
    if st.button("최종 승인 후 패키지 만들기", disabled=not st.session_state.card_paths):
        _widgets_into_plan_dict()
        plan_d = st.session_state.plan_dict
        if not plan_d:
            st.error("기획안 없음")
            st.stop()
        paths_ko = [Path(p) for p in st.session_state.card_paths if Path(p).exists()]
        paths_en = [Path(p) for p in st.session_state.get("card_paths_en", []) if Path(p).exists()]
        paths = paths_ko + paths_en
        if not paths:
            st.error("JPEG 파일을 찾을 수 없습니다.")
            st.stop()
        cards_root = out_root / "cards"
        zip_bytes = build_export_zip_bytes(plan_d, paths, cards_root=cards_root if cards_root.exists() else None)
        fname = f"cardnews_export_{datetime.now().strftime('%Y%m%d_%H%M')}.zip"
        st.download_button(
            label=f"ZIP 다운로드 ({fname})",
            data=zip_bytes,
            file_name=fname,
            mime="application/zip",
        )
        pptx_only = build_plan_pptx_bytes(CardNewsPlan.model_validate(plan_d))
        st.download_button(
            label="기획안 PPTX만 받기",
            data=pptx_only,
            file_name="기획안_최종.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )

    if _SNS_READY and st.session_state.card_paths:
        _render_section_instagram_upload(client)


def _render_section_instagram_upload(client: OpenAI) -> None:
    st.divider()
    st.subheader("7. 인스타그램 자동 업로드 (Buffer)")

    paths_ko = [Path(p) for p in st.session_state.card_paths if Path(p).exists()]
    if not paths_ko:
        st.info("렌더된 한국어 카드가 없습니다. 먼저 카드 생성을 마치세요.")
        return
    if len(paths_ko) > 10:
        st.error(
            f"카드 {len(paths_ko)}장 — Instagram 캐러셀은 최대 10장. 페이지 수를 줄여 다시 렌더하세요."
        )
        return

    already_posted = bool(st.session_state.get("instagram_uploaded_post_id"))
    if already_posted:
        st.success(
            f"이미 발행 완료. post_id={st.session_state.instagram_uploaded_post_id}"
        )

    col_a, col_b = st.columns([1, 3])
    with col_a:
        if st.button("캡션 초안 생성", disabled=already_posted, key="btn_caption_draft"):
            try:
                with st.spinner("캡션 생성 중..."):
                    caption = generate_instagram_caption(
                        client,
                        st.session_state.get("press_text", ""),
                        st.session_state.get("plan_dict"),
                    )
                st.session_state.instagram_caption = caption
            except ContentFilterError as exc:
                st.error(f"캡션 안전 필터 차단:\n\n{exc}")
            except Exception as exc:
                st.error(f"캡션 생성 실패: {exc}")
    with col_b:
        st.caption(
            "PDF 본문 + 기획안을 근거로 OpenAI가 한국어 캡션 초안을 작성합니다. "
            "작성 요령은 `code/caption_llm.py`의 `DEFAULT_CAPTION_SYSTEM_PROMPT`를 편집해 조정하세요."
        )

    st.text_area(
        "Instagram 캡션",
        key="instagram_caption",
        height=240,
        max_chars=MAX_CAPTION_LEN,
        disabled=already_posted,
    )
    caption_len = len(st.session_state.get("instagram_caption", ""))
    st.caption(f"{caption_len} / {MAX_CAPTION_LEN}자")

    upload_disabled = (
        already_posted
        or caption_len == 0
        or caption_len > MAX_CAPTION_LEN
    )
    if st.button(
        "인스타그램 업로드",
        disabled=upload_disabled,
        key="btn_instagram_upload",
        type="primary",
    ):
        _do_instagram_upload(paths_ko)

    pending_keys = st.session_state.get("instagram_uploaded_keys") or []
    has_post = bool(st.session_state.get("instagram_uploaded_post_id"))
    if has_post and pending_keys and not st.session_state.get("instagram_cleanup_done"):
        st.divider()
        st.caption(f"Supabase 잔존 파일 {len(pending_keys)}개")
        if st.button("Supabase 임시 파일 정리", key="btn_supabase_cleanup"):
            try:
                delete_objects(pending_keys)
                st.session_state.instagram_cleanup_done = True
                st.session_state.instagram_uploaded_keys = []
                _persist()
                st.success("Supabase 임시 파일 삭제 완료.")
            except Exception as ce:
                st.error(f"삭제 실패: {ce}")


def _do_instagram_upload(paths_ko: list[Path]) -> None:
    caption = st.session_state.get("instagram_caption", "").strip()
    session_id = st.session_state.session_id
    assets: list[UploadedAsset] = []
    try:
        with st.spinner("Supabase 업로드 중..."):
            assets = upload_card_images(paths_ko, session_id)
        with st.spinner("Buffer 발행 요청 중..."):
            post_id = create_instagram_post(
                BUFFER_CHANNEL_ID,
                [a.url for a in assets],
                caption,
            )
        st.session_state.instagram_uploaded_post_id = post_id
        st.session_state.instagram_uploaded_keys = [a.key for a in assets]
        _persist()
        st.success(f"발행 완료. post_id={post_id}")
        st.info(
            "Buffer가 비동기로 이미지를 가져가 Instagram에 업로드합니다(수초~수분 소요). "
            "Instagram에 게시물이 정상 노출된 뒤 아래 'Supabase 임시 파일 정리' 버튼으로 원격 파일을 삭제하세요."
        )
    except SupabaseStorageError as exc:
        st.error(f"Supabase 업로드 실패: {exc}")
        if assets:
            try:
                delete_objects([a.key for a in assets])
            except Exception:
                pass
    except BufferError as exc:
        st.error(f"Buffer 발행 실패: {exc}")
        if assets:
            try:
                delete_objects([a.key for a in assets])
            except Exception:
                pass
    except Exception as exc:
        st.error(f"업로드 실패: {exc}")


if __name__ == "__main__":
    main()
