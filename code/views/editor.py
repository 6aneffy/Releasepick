"""Editor page: 5-step workflow (stitch _2 layout + stitch _3 result step)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from buffer_publish import BufferError, create_instagram_post
from caption_llm import (
    MAX_CAPTION_LEN,
    generate_instagram_caption,
)
from content_filter import ContentFilterError
from image_gen import (
    ENGLISH_LOGO_WORDMARK,
    build_theme_description,
    generate_plan_card_jpegs,
    image_models_for_selectbox,
    resolve_model,
)
from pdf_extract import extract_text_from_pdf_bytes
from plan_llm import generate_plan, translate_plan_to_english
from render_cards import list_theme_ids
from supabase_storage import (
    SupabaseStorageError,
    UploadedAsset,
    delete_objects,
    upload_card_images,
)
from template_catalog import (
    concept_image_block,
    concept_plan_block,
    concepts_for_pages,
    get_concept,
    load_one_page_template_text,
    page_group,
    recommend_concept_id,
)
from template_resources import (
    DEFAULT_MULTIPAGE_VARIANT,
    load_body_template_text,
    load_cover_template_text,
    multipage_variant_labels,
)
from template_thumbnails import generate_thumbnails_for_pages

from state import (
    guard_plan,
    init_session,
    persist,
    plan_to_text,
    reset_session,
    seed_page_widgets_from_plan,
    try_hydrate,
    widgets_into_plan_dict,
)
from ui.components import (
    footer,
    pill,
    section_header,
    step_nav,
    top_app_bar,
)
from ui.theme import inject_global_css
from views import result_view


CODE_DIR = Path(__file__).resolve().parents[1]
ROOT = CODE_DIR.parent
load_dotenv(dotenv_path=ROOT / ".env", override=False)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "").strip()
BUFFER_API_KEY = os.getenv("BUFFER_API_KEY", "").strip()
BUFFER_CHANNEL_ID = os.getenv("BUFFER_CHANNEL_ID", "").strip()
_SNS_READY = bool(
    SUPABASE_URL
    and SUPABASE_SERVICE_ROLE_KEY
    and SUPABASE_BUCKET
    and BUFFER_API_KEY
    and BUFFER_CHANNEL_ID
)


# ---------- Helpers ----------

def _resolve_design_templates(
    target_pages: int, multipage_variant: str
) -> tuple[str, str, bool]:
    """1장이면 포스터 템플릿만, 2장 이상이면 선택한 변형 (v1/v2) 의 표지·본문.

    Returns (cover_full, body_full, single_page).
    """
    if target_pages == 1:
        return load_one_page_template_text(), "", True
    return (
        load_cover_template_text(multipage_variant),
        load_body_template_text(multipage_variant),
        False,
    )


# ---------- Step bodies ----------

def step_upload(client: OpenAI) -> None:
    section_header(1, "보도자료 PDF 업로드")
    st.caption("지원 형식: PDF, HWP, HWPX, DOCX (최대 50MB)")

    up = st.file_uploader(
        "여기에 보도자료를 끌어오거나 파일을 선택하세요",
        type=["pdf"],
        label_visibility="collapsed",
    )
    if up:
        st.session_state.pdf_bytes = up.getvalue()
        st.session_state.pdf_name = up.name
        persist()

    if st.session_state.pdf_bytes:
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                st.markdown(
                    f"📄 **{st.session_state.pdf_name}**"
                    f"<br/><span style='font-size:12px;color:var(--rp-on-surface-variant)'>"
                    f"{len(st.session_state.pdf_bytes) // 1024} KB</span>",
                    unsafe_allow_html=True,
                )
            with c2:
                st.markdown(pill("업로드 완료", "ok"), unsafe_allow_html=True)
            with c3:
                if st.button("텍스트 추출", use_container_width=True, key="extract_btn"):
                    with st.spinner("추출 중…"):
                        st.session_state.press_text = extract_text_from_pdf_bytes(
                            st.session_state.pdf_bytes
                        )
                    if not st.session_state.press_text.strip():
                        st.warning("추출된 텍스트가 없습니다. 스캔 PDF일 수 있습니다.")
                    else:
                        st.success(f"추출 완료 ({len(st.session_state.press_text)}자)")
                    persist()

    if st.session_state.press_text:
        with st.expander("추출 텍스트 미리보기"):
            st.text(st.session_state.press_text[:8000])

    st.divider()
    with st.container(border=True):
        st.markdown("##### 카드뉴스 페이지 수")
        target_pages = st.slider(
            "총 페이지 수 (슬라이드)",
            min_value=1,
            max_value=12,
            value=int(st.session_state.get("target_pages", 5)),
        )
        st.session_state.target_pages = int(target_pages)

        pg_group = page_group(target_pages)
        if st.session_state.get("target_pages_group") != pg_group:
            st.session_state.target_pages_group = pg_group
            st.session_state.concept_template_id = None
            st.session_state.concept_confirmed = False
            st.session_state.concept_thumb_paths = {}

        if target_pages == 1:
            st.caption("1장 제작 — 포스터형 템플릿 (`themes/template1/템플릿-1.txt`) 적용")
            st.session_state.multipage_variant = DEFAULT_MULTIPAGE_VARIANT
        else:
            v_labels = multipage_variant_labels()
            v_ids = list(v_labels.keys())
            cur = st.session_state.get("multipage_variant", DEFAULT_MULTIPAGE_VARIANT)
            chosen = st.radio(
                "디자인 템플릿 (2장 이상)",
                v_ids,
                index=v_ids.index(cur) if cur in v_ids else 0,
                format_func=lambda v: v_labels.get(v, v),
                horizontal=True,
                key="multipage_variant_radio",
            )
            st.session_state.multipage_variant = chosen
            st.caption(
                "선택한 템플릿이 기획안·카드 생성에 모두 적용됩니다. "
                "변경 시 기획·카드를 다시 생성하세요."
            )


def step_plan(client: OpenAI) -> None:
    section_header(2, "내용 분석 · 기획안")

    target_pages = st.session_state.get("target_pages", 5)
    concept_id = (
        st.session_state.concept_template_id
        if st.session_state.concept_confirmed
        else None
    )
    plan_block = concept_plan_block(concept_id)

    can_generate = bool(st.session_state.press_text and st.session_state.press_text.strip())
    if st.button(
        "AI 분석 시작",
        type="primary",
        disabled=not can_generate,
        key="plan_gen_btn",
    ):
        try:
            with st.spinner("LLM 기획 작성 → 안전 필터 검사…"):
                plan = generate_plan(
                    client,
                    st.session_state.press_text,
                    target_pages=target_pages,
                    concept_style_block=plan_block,
                    template_variant=st.session_state.get(
                        "multipage_variant", DEFAULT_MULTIPAGE_VARIANT
                    ),
                )
                st.session_state.plan_dict = plan.to_json_dict()
                st.session_state.plan_phase = "draft"
                st.session_state.plan_first_approved = False
                st.session_state.plan_revisions_remaining = 0
                st.session_state.plan_bump = st.session_state.get("plan_bump", 0) + 1
                st.session_state._seed_bump = -1
                plan_to_text()
            st.success("기획안 생성 완료 (안전 필터 통과)")
            persist()
            st.rerun()
        except ContentFilterError as exc:
            st.error(str(exc))
            st.stop()

    plan_locked = st.session_state.plan_phase == "locked"
    plan_readonly = plan_locked or (
        st.session_state.plan_phase == "post_first"
        and st.session_state.plan_revisions_remaining <= 0
    )

    if st.session_state.plan_dict:
        bump = st.session_state.get("plan_bump", 0)
        if st.session_state.get("_seed_bump", -1) != bump:
            seed_page_widgets_from_plan()
            st.session_state._seed_bump = bump

        st.markdown("##### 페이지별 내용")
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
                st.text_input(
                    "슬라이드 제목", key=f"pg_{i}_title", disabled=plan_readonly
                )
                st.text_area(
                    "불릿 (줄마다 하나)",
                    key=f"pg_{i}_bullets",
                    height=120,
                    disabled=plan_readonly,
                )
                st.text_input(
                    "각주 (선택)", key=f"pg_{i}_footnote", disabled=plan_readonly
                )

        ga, gb, gc = st.columns(3)
        with ga:
            if st.button(
                "페이지 편집 반영",
                disabled=plan_readonly,
                use_container_width=True,
            ):
                widgets_into_plan_dict()
                if not guard_plan(st.session_state.plan_dict, context="기획 반영"):
                    st.stop()
                persist()
                st.success("기획안이 업데이트되었습니다.")
        with gb:
            if st.button(
                "1차 승인",
                disabled=(
                    st.session_state.plan_dict is None
                    or st.session_state.plan_phase != "draft"
                ),
                use_container_width=True,
            ):
                widgets_into_plan_dict()
                if not guard_plan(st.session_state.plan_dict, context="기획 1차 승인"):
                    st.stop()
                st.session_state.plan_phase = "post_first"
                st.session_state.plan_revisions_remaining = 2
                st.session_state.plan_first_approved = True
                persist()
                st.rerun()
        with gc:
            if st.button(
                "기획 확정 →",
                type="primary",
                disabled=(
                    st.session_state.plan_dict is None
                    or st.session_state.plan_phase == "draft"
                    or plan_locked
                ),
                use_container_width=True,
            ):
                widgets_into_plan_dict()
                if not guard_plan(st.session_state.plan_dict, context="기획 확정"):
                    st.stop()
                st.session_state.plan_phase = "locked"
                persist()
                st.rerun()

        if st.session_state.plan_phase == "post_first":
            if st.button(
                f"수정 반영 (남은 횟수 {st.session_state.plan_revisions_remaining})",
                disabled=st.session_state.plan_revisions_remaining <= 0 or plan_locked,
                key="plan_revise_btn",
            ):
                widgets_into_plan_dict()
                st.session_state.plan_revisions_remaining -= 1
                persist()
                st.rerun()

        with st.expander("고급: JSON 보기"):
            st.code(st.session_state.get("plan_text", "") or "", language="json")


def step_design(client: OpenAI) -> None:
    section_header(3, "디자인 설정")

    target_pages = st.session_state.get("target_pages", 5)
    concepts = concepts_for_pages(target_pages)

    # Auto-confirm a recommended concept silently — no UI shown
    recommended_id = recommend_concept_id(
        st.session_state.press_text or "", target_pages
    )
    valid_ids = {c.id for c in concepts}
    if st.session_state.get("concept_template_id") not in valid_ids:
        st.session_state.concept_template_id = recommended_id
    st.session_state.concept_confirmed = True

    def _group_head(icon: str, title: str) -> None:
        st.markdown(
            f'<div class="rp-group-head">'
            f'<span class="material-symbols-outlined">{icon}</span>'
            f'<span>{title}</span></div>',
            unsafe_allow_html=True,
        )

    # Row 1: 템플릿 & 컬러 톤 | 로고 & 캐릭터
    r1c1, r1c2 = st.columns(2, gap="medium")
    with r1c1:
        st.markdown('<div class="rp-design-row-marker"></div>', unsafe_allow_html=True)
        with st.container(border=True):
            _group_head("palette", "템플릿 & 컬러 톤")
            themes = list_theme_ids()
            st.selectbox(
                "템플릿 (YAML)", themes, index=0, key="dc_theme",
                label_visibility="visible",
            )
            tone_options = ["neutral", "green", "blue", "purple", "orange"]
            tone_labels = {
                "neutral": "기본", "green": "녹색", "blue": "파랑",
                "purple": "보라", "orange": "주황",
            }
            tone_swatches = {
                "neutral": "#94a3b8", "green": "#16a34a", "blue": "#2563eb",
                "purple": "#7c3aed", "orange": "#ea580c",
            }
            current_tone = st.session_state.get("dc_tone", "blue")
            st.markdown(
                '<div class="rp-tone-label">섹션 컬러 톤</div>',
                unsafe_allow_html=True,
            )
            swatch_cols = st.columns(len(tone_options))
            for i, tn in enumerate(tone_options):
                with swatch_cols[i]:
                    is_sel = tn == current_tone
                    clicked = st.button(
                        "✓" if is_sel else " ",
                        key=f"tone_btn_{tn}",
                        use_container_width=True,
                        type="primary" if is_sel else "secondary",
                    )
                    if clicked:
                        st.session_state.dc_tone = tn
                        st.rerun()
                    sel = " sel" if is_sel else ""
                    st.markdown(
                        f'<div class="rp-tone-name{sel}">{tone_labels[tn]}</div>',
                        unsafe_allow_html=True,
                    )

    with r1c2:
        with st.container(border=True):
            _group_head("location_on", "로고 & 캐릭터")
            st.radio(
                "로고 위치",
                ["top_right", "top_left", "bottom_center"],
                horizontal=True,
                key="dc_logo",
                label_visibility="collapsed",
            )
            char_file = st.file_uploader(
                "캐릭터 PNG (선택)", type=["png"], key="dc_char"
            )
            if char_file:
                st.session_state.character_bytes = char_file.getvalue()

    # Row 2: 텍스트 색상 | 본문 레이아웃
    r2c1, r2c2 = st.columns(2, gap="medium")
    with r2c1:
        st.markdown('<div class="rp-design-row-marker"></div>', unsafe_allow_html=True)
        with st.container(border=True):
            _group_head("format_color_text", "텍스트 색상")
            cc1, cc2 = st.columns(2)
            with cc1:
                st.color_picker("제목 색", value="#111111", key="dc_tcol")
                st.checkbox("제목 색 반영", value=False, key="dc_ut")
            with cc2:
                st.color_picker("본문 색", value="#333333", key="dc_bcol")
                st.checkbox("본문 색 반영", value=False, key="dc_ub")

    with r2c2:
        with st.container(border=True):
            _group_head("dashboard", "본문 레이아웃")
            st.radio(
                "레이아웃",
                ["여백형 (패턴 A)", "흰 카드형 (패턴 B)"],
                horizontal=True,
                key="dc_layout",
                label_visibility="collapsed",
            )
            st.markdown(
                '<div class="rp-tone-label" style="margin-top:0.75rem">폰트 크기 배율</div>',
                unsafe_allow_html=True,
            )
            st.slider(
                "배율", 0.75, 1.25, 1.0, 0.05,
                key="dc_fscale", label_visibility="collapsed",
            )

    # Row 3 — model
    with st.container(border=True):
        _group_head("auto_awesome", "이미지 생성 모델")
        st.selectbox(
            "모델",
            image_models_for_selectbox(),
            index=0,
            key="dc_imgmodel",
            label_visibility="collapsed",
        )


def _build_design_args() -> dict:
    body_layout_label = st.session_state.get("dc_layout", "여백형 (패턴 A)")
    return {
        "theme_id": st.session_state.get("dc_theme", "mofe_body"),
        "section_tone": st.session_state.get("dc_tone", "blue"),
        "body_layout": "simple" if "A" in body_layout_label else "white_card",
        "font_scale": st.session_state.get("dc_fscale", 1.0),
        "use_custom_title": st.session_state.get("dc_ut", False),
        "use_custom_body": st.session_state.get("dc_ub", False),
        "title_color": st.session_state.get("dc_tcol", "#111111"),
        "body_color": st.session_state.get("dc_bcol", "#333333"),
        "logo_pos": st.session_state.get("dc_logo", "top_right"),
    }


def step_generate(client: OpenAI) -> None:
    section_header(4, "카드 이미지 생성 (JPEG)")

    img_model_label = st.session_state.get("dc_imgmodel") or image_models_for_selectbox()[0]
    img_model = resolve_model(img_model_label)

    da = _build_design_args()
    theme_desc = build_theme_description(**da)
    img_concept_block = concept_image_block(
        st.session_state.concept_template_id
        if st.session_state.concept_confirmed
        else None
    )

    st.caption(
        f"동일 템플릿·디자인으로 **한국어 세트** 생성 후 번역해 **영어 세트** 생성. "
        f"한·영 모두 GPT Image가 정부 로고를 그립니다. 영문은 「{ENGLISH_LOGO_WORDMARK}」."
    )
    with st.expander("정서·이미지 안전 필터 안내"):
        st.markdown(
            "- 기획·프롬프트·생성 단계에서 일본·식민지 잔재, 북한·분단, 정치 이념·갈등, 혐오 표현 차단\n"
            "- 통과하지 않은 기획은 API 호출 없이 중단"
        )

    out_root = (
        Path(tempfile.gettempdir())
        / "cardnews_exports"
        / st.session_state.session_id
    )
    out_root.mkdir(parents=True, exist_ok=True)
    st.session_state["_out_root"] = str(out_root)

    can_generate = (
        st.session_state.plan_phase == "locked"
        and st.session_state.plan_dict is not None
    )
    if not can_generate:
        st.warning("이전 단계에서 **기획 확정**을 먼저 완료하세요.")

    if st.button(
        "카드 생성 시작",
        type="primary",
        disabled=not can_generate,
        key="gen_first_btn",
    ):
        widgets_into_plan_dict()
        plan_d = st.session_state.plan_dict
        if not plan_d or not guard_plan(plan_d, context="카드 생성"):
            st.stop()
        target_pages = st.session_state.get("target_pages", 5)
        mv = st.session_state.get("multipage_variant", DEFAULT_MULTIPAGE_VARIANT)
        cover_full, body_full, single_page = _resolve_design_templates(
            target_pages, mv
        )
        if not cover_full.strip():
            st.error("템플릿 파일을 찾을 수 없습니다.")
            st.stop()
        title_color = da["title_color"] if da["use_custom_title"] else None
        body_color = da["body_color"] if da["use_custom_body"] else None
        prog = st.progress(0)
        try:
            nslides = len(plan_d.get("slides") or [])
            total_steps = max(1, nslides * 2)
            done = [0]

            def _p(_c: int, _t: int) -> None:
                done[0] += 1
                prog.progress(min(1.0, done[0] / total_steps))

            ko_dir = out_root / "cards" / "ko"
            en_dir = out_root / "cards" / "en"
            ko_dir.mkdir(parents=True, exist_ok=True)
            en_dir.mkdir(parents=True, exist_ok=True)

            common = dict(
                theme_desc=theme_desc,
                cover_template_full=cover_full,
                body_template_full=body_full,
                progress_callback=_p if nslides else None,
                section_tone=da["section_tone"],
                theme_id=da["theme_id"],
                logo_pos=da["logo_pos"],
                concept_style_block=img_concept_block,
                single_page_template=single_page,
                title_color=title_color,
                body_color=body_color,
            )
            with st.spinner(f"한국어 카드 생성 중… ({img_model})"):
                paths_ko = generate_plan_card_jpegs(
                    client, img_model, plan_d,
                    out_dir=ko_dir, copy_locale="ko", **common,
                )
            st.session_state.card_paths = [str(p) for p in paths_ko]
            persist()

            paths_en: list[Path] = []
            try:
                with st.spinner(f"영어 카드 생성 중… ({img_model})"):
                    plan_en = translate_plan_to_english(client, plan_d)
                    paths_en = generate_plan_card_jpegs(
                        client, img_model, plan_en,
                        out_dir=en_dir, copy_locale="en", **common,
                    )
                st.session_state.card_paths_en = [str(p) for p in paths_en]
            except Exception as exc:
                st.warning(f"영어 카드 생성 실패 (한국어는 정상): {exc}")

            st.session_state.card_review_approved = False
            st.session_state.card_revisions_remaining = 0
            st.success(
                f"한국어 {len(paths_ko)}장 + 영어 {len(paths_en)}장 생성 완료"
            )
            persist()
        except ContentFilterError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"이미지 생성 실패: {exc}")
        finally:
            prog.empty()
        st.rerun()

    if st.session_state.card_paths:
        n_ko = len(st.session_state.card_paths)
        n_en = len(st.session_state.get("card_paths_en") or [])
        st.success(
            f"카드 생성 완료 — 한국어 {n_ko}장 · 영어 {n_en}장. "
            "**다음 →** 으로 결과를 확인하세요."
        )


# ---------- Step 6: SNS upload (Instagram via Buffer + Supabase) ----------

def _do_instagram_upload(paths_ko: list[Path]) -> None:
    caption = st.session_state.get("instagram_caption", "").strip()
    session_id = st.session_state.session_id
    assets: list[UploadedAsset] = []
    try:
        with st.spinner("이미지 업로드 중..."):
            assets = upload_card_images(paths_ko, session_id)
        with st.spinner("인스타그램 발행 요청 중..."):
            post_id = create_instagram_post(
                BUFFER_CHANNEL_ID,
                [a.url for a in assets],
                caption,
            )
        st.session_state.instagram_uploaded_post_id = post_id
        st.session_state.instagram_uploaded_keys = [a.key for a in assets]
        persist()
        st.success(f"발행 완료. post_id={post_id}")
        st.info(
            "정상 노출 확인 후 아래 '임시 파일 정리' 로 원격 파일을 삭제하세요."
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


def step_sns(client: OpenAI) -> None:
    section_header(6, "SNS 업로드")

    if not _SNS_READY:
        st.warning(
            "SNS 업로드 환경변수 미설정. `.env` 에 `SUPABASE_URL`, "
            "`SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_BUCKET`, "
            "`BUFFER_API_KEY`, `BUFFER_CHANNEL_ID` 를 설정하세요."
        )
        return

    paths_ko = [Path(p) for p in st.session_state.card_paths if Path(p).exists()]
    if not paths_ko:
        st.info("렌더된 한국어 카드가 없습니다. 이전 단계에서 카드 생성을 완료하세요.")
        return
    if len(paths_ko) > 10:
        st.error(
            f"카드 {len(paths_ko)}장 — Instagram 캐러셀 최대 10장. 페이지 수를 줄여 다시 렌더."
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
                persist()
            except ContentFilterError as exc:
                st.error(f"캡션 안전 필터 차단:\n\n{exc}")
            except Exception as exc:
                st.error(f"캡션 생성 실패: {exc}")
    with col_b:
        st.caption(
            "PDF 본문 + 기획안 기반으로 OpenAI 가 한국어 캡션 초안 작성. "
            "프롬프트는 `code/caption_llm.py` 에서 조정."
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
        already_posted or caption_len == 0 or caption_len > MAX_CAPTION_LEN
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
                persist()
                st.success("Supabase 임시 파일 삭제 완료.")
            except Exception as ce:
                st.error(f"삭제 실패: {ce}")


# ---------- Step transition footer ----------

def step_footer() -> None:
    step = st.session_state.editor_step
    st.divider()
    c_prev, c_spacer, c_next = st.columns([1, 5, 1])
    with c_prev:
        if step > 1:
            if st.button("← 이전", use_container_width=True, key=f"prev_{step}"):
                st.session_state.editor_step = step - 1
                persist()
                st.rerun()
    with c_next:
        if step < 6:
            disabled = _next_disabled(step)
            if st.button(
                "다음 →",
                type="primary",
                disabled=disabled,
                use_container_width=True,
                key=f"next_{step}",
            ):
                st.session_state.editor_step = step + 1
                persist()
                st.rerun()


def _next_disabled(step: int) -> bool:
    if step == 1:
        return not bool(st.session_state.press_text and st.session_state.press_text.strip())
    if step == 2:
        return st.session_state.plan_phase != "locked"
    if step == 3:
        return not bool(st.session_state.concept_confirmed)
    if step == 4:
        return not bool(st.session_state.card_paths)
    if step == 5:
        return not bool(st.session_state.card_paths)
    return True


# ---------- Page entry ----------

def render() -> None:
    inject_global_css()
    init_session()
    try_hydrate()
    nav = st.query_params.get("nav")
    if nav == "home":
        st.query_params.clear()
        st.switch_page("views/landing.py")
    elif nav == "editor":
        st.query_params.clear()
    top_app_bar(active="editor")

    if not OPENAI_API_KEY:
        st.error("`.env` 에 `OPENAI_API_KEY` 를 설정하세요. (저장소 루트 `Releasepick/.env`)")
        st.stop()
    client = OpenAI(api_key=OPENAI_API_KEY)

    nav_col, work_col = st.columns([1.1, 4], gap="medium")
    with nav_col:
        completed = {n for n in range(1, st.session_state.editor_step)}
        step_nav(current=st.session_state.editor_step, completed=completed)
        if st.button(
            "세션 초기화",
            use_container_width=True,
            key="reset_session_btn",
        ):
            reset_session()
            st.rerun()

    with work_col:
        step = st.session_state.editor_step
        if step == 1:
            step_upload(client)
        elif step == 2:
            step_plan(client)
        elif step == 3:
            step_design(client)
        elif step == 4:
            step_generate(client)
        elif step == 5:
            result_view.render(client)
        elif step == 6:
            step_sns(client)
        step_footer()

    footer()


render()
