"""Result step (stitch _3): thumb rail + preview + edit panel + actions."""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

import streamlit as st
from openai import OpenAI

from content_filter import ContentFilterError
from export_plan_pptx import build_plan_pptx_bytes
from image_gen import (
    build_theme_description,
    generate_plan_card_jpegs,
    image_models_for_selectbox,
    resolve_model,
)
from models import CardNewsPlan
from package_export import build_export_zip_bytes
from plan_llm import translate_plan_to_english
from template_catalog import concept_image_block, load_one_page_template_text
from template_resources import (
    DEFAULT_MULTIPAGE_VARIANT,
    load_body_template_text,
    load_cover_template_text,
)

from state import guard_plan, persist, widgets_into_plan_dict
from ui.components import panel_title, pill, section_header


def _design_args() -> dict:
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


def _current_paths(locale: str) -> list[str]:
    return list(
        st.session_state.get(
            "card_paths" if locale == "ko" else "card_paths_en", []
        )
    )


def _thumb_rail(locale: str) -> None:
    paths = _current_paths(locale)
    if not paths:
        st.caption("생성된 카드가 없습니다.")
        return
    active = int(st.session_state.get("result_active_idx", 0))
    active = min(active, max(0, len(paths) - 1))
    for i, p in enumerate(paths):
        if not Path(p).exists():
            continue
        is_active = i == active
        with st.container(border=is_active):
            st.image(p, use_container_width=True)
            if st.button(
                f"페이지 {i + 1}",
                key=f"thumb_{locale}_{i}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state.result_active_idx = i
                st.rerun()


def _preview(locale: str) -> None:
    paths = _current_paths(locale)
    active = int(st.session_state.get("result_active_idx", 0))
    if not paths:
        with st.container(border=True):
            st.markdown(
                '<div style="min-height:400px;display:flex;align-items:center;'
                'justify-content:center;color:var(--rp-on-surface-variant);'
                'text-align:center">'
                '카드가 아직 생성되지 않았습니다.<br/>'
                '이전 단계에서 카드를 생성하세요.</div>',
                unsafe_allow_html=True,
            )
        return
    active = min(active, max(0, len(paths) - 1))
    p = paths[active]
    if Path(p).exists():
        with st.container(border=True):
            st.image(p, use_container_width=True)
        st.caption(f"페이지 {active + 1} / {len(paths)} · {locale.upper()}")


def _edit_panel(locale: str) -> None:
    with st.container(border=True):
        panel_title("콘텐츠 편집")
        plan_d = st.session_state.plan_dict
        if not plan_d:
            st.caption("기획 데이터 없음")
            return
        slides = plan_d.get("slides") or []
        idx = int(st.session_state.get("result_active_idx", 0))
        idx = min(idx, max(0, len(slides) - 1))
        if not slides:
            st.caption("슬라이드 없음")
            return
        slide = slides[idx]
        st.text_input(
            f"페이지 {idx + 1} 제목",
            value=str(slide.get("title", "")),
            key=f"rv_title_{idx}",
        )
        st.text_area(
            "내용 (불릿, 줄마다 하나)",
            value="\n".join(slide.get("bullets") or []),
            key=f"rv_bullets_{idx}",
            height=140,
        )
        st.text_input(
            "각주 (선택)",
            value=str(slide.get("footnote") or ""),
            key=f"rv_footnote_{idx}",
        )
        if st.button("이 페이지 변경 반영", key=f"rv_apply_{idx}", use_container_width=True):
            slide["title"] = st.session_state.get(f"rv_title_{idx}", "")
            bl = st.session_state.get(f"rv_bullets_{idx}", "")
            slide["bullets"] = [ln.strip() for ln in str(bl).splitlines() if ln.strip()]
            fn = str(st.session_state.get(f"rv_footnote_{idx}", "")).strip()
            slide["footnote"] = fn or None
            persist()
            st.toast("기획안에 반영했습니다. 전체 재생성 시 적용됩니다.")

    with st.container(border=True):
        panel_title("스타일 및 색상")
        swatches = ["#2563eb", "#0f766e", "#7c3aed", "#ea580c", "#dc2626", "#111827", "#6b7280"]
        st.markdown(
            "".join(
                f'<span style="display:inline-block;width:28px;height:28px;'
                f"border-radius:50%;background:{c};margin-right:6px;"
                f'border:1px solid var(--rp-outline-variant)"></span>'
                for c in swatches
            ),
            unsafe_allow_html=True,
        )
        st.caption("팔레트 변경은 디자인 설정 단계에서 적용됩니다.")


def _regenerate_all(client: OpenAI) -> None:
    widgets_into_plan_dict()
    plan_d = st.session_state.plan_dict
    if not plan_d or not guard_plan(plan_d, context="카드 다시 생성"):
        st.stop()
    target_pages = st.session_state.get("target_pages", 5)
    mv = st.session_state.get("multipage_variant", DEFAULT_MULTIPAGE_VARIANT)
    if target_pages == 1:
        cover_full = load_one_page_template_text()
        body_full = ""
        single_page = True
    else:
        cover_full = load_cover_template_text(mv)
        body_full = load_body_template_text(mv)
        single_page = False
    if not cover_full.strip():
        st.error("템플릿 파일을 찾을 수 없습니다.")
        st.stop()

    out_root = Path(
        st.session_state.get("_out_root")
        or (Path(tempfile.gettempdir()) / "cardnews_exports" / st.session_state.session_id)
    )
    ko_dir = out_root / "cards" / "ko"
    en_dir = out_root / "cards" / "en"
    ko_dir.mkdir(parents=True, exist_ok=True)
    en_dir.mkdir(parents=True, exist_ok=True)

    img_model_label = st.session_state.get("dc_imgmodel") or image_models_for_selectbox()[0]
    img_model = resolve_model(img_model_label)
    da = _design_args()
    theme_desc = build_theme_description(**da)
    img_concept_block = concept_image_block(
        st.session_state.concept_template_id
        if st.session_state.concept_confirmed
        else None
    )
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
        with st.spinner(f"한국어 카드 재생성… ({img_model})"):
            paths_ko = generate_plan_card_jpegs(
                client, img_model, plan_d,
                out_dir=ko_dir, copy_locale="ko", **common,
            )
        st.session_state.card_paths = [str(p) for p in paths_ko]
        persist()
        try:
            with st.spinner(f"영어 카드 재생성… ({img_model})"):
                plan_en = translate_plan_to_english(client, plan_d)
                paths_en = generate_plan_card_jpegs(
                    client, img_model, plan_en,
                    out_dir=en_dir, copy_locale="en", **common,
                )
            st.session_state.card_paths_en = [str(p) for p in paths_en]
        except Exception as exc:
            st.warning(f"영어 카드 재생성 실패 (한국어는 정상): {exc}")
        if st.session_state.card_revisions_remaining > 0:
            st.session_state.card_revisions_remaining -= 1
        persist()
        st.toast("재생성 완료")
    except ContentFilterError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(f"재생성 실패: {exc}")
    finally:
        prog.empty()
    st.rerun()


def _action_bar(client: OpenAI) -> None:
    st.divider()
    plan_d = st.session_state.plan_dict
    paths_ko = [Path(p) for p in st.session_state.card_paths if Path(p).exists()]
    paths_en = [
        Path(p) for p in st.session_state.get("card_paths_en", []) if Path(p).exists()
    ]

    a, b, c, d = st.columns(4)

    with a:
        st.button(
            "선택 페이지 다시 생성",
            disabled=True,
            help="현재 버전은 전체 재생성만 지원합니다.",
            use_container_width=True,
        )

    with b:
        approved = st.session_state.card_review_approved
        if not approved:
            if st.button(
                "검토 승인 (재생성 2회)",
                disabled=not paths_ko,
                use_container_width=True,
                key="rv_approve_btn",
            ):
                st.session_state.card_review_approved = True
                st.session_state.card_revisions_remaining = 2
                persist()
                st.rerun()
        else:
            if st.button(
                f"전체 재생성 (남은 {st.session_state.card_revisions_remaining})",
                disabled=st.session_state.card_revisions_remaining <= 0,
                use_container_width=True,
                key="rv_regen_btn",
            ):
                _regenerate_all(client)

    with c:
        if plan_d:
            try:
                pptx_bytes = build_plan_pptx_bytes(CardNewsPlan.model_validate(plan_d))
                st.download_button(
                    "PDF 내려받기 (PPTX)",
                    data=pptx_bytes,
                    file_name="기획안_최종.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True,
                    key="rv_pptx_dl",
                )
            except Exception:
                st.button("PDF 내려받기", disabled=True, use_container_width=True)
        else:
            st.button("PDF 내려받기", disabled=True, use_container_width=True)

    with d:
        all_paths = paths_ko + paths_en
        if plan_d and all_paths:
            out_root_str = st.session_state.get("_out_root")
            cards_root = Path(out_root_str) / "cards" if out_root_str else None
            try:
                zip_bytes = build_export_zip_bytes(
                    plan_d,
                    all_paths,
                    cards_root=cards_root if cards_root and cards_root.exists() else None,
                )
                fname = f"cardnews_export_{datetime.now().strftime('%Y%m%d_%H%M')}.zip"
                st.download_button(
                    "PNG 다운로드 (ZIP)",
                    data=zip_bytes,
                    file_name=fname,
                    mime="application/zip",
                    type="primary",
                    use_container_width=True,
                    key="rv_zip_dl",
                )
            except Exception:
                st.button("PNG 다운로드", disabled=True, use_container_width=True)
        else:
            st.button(
                "PNG 다운로드",
                disabled=True,
                use_container_width=True,
                key="rv_zip_dl_disabled",
            )


def render(client: OpenAI) -> None:
    head_l, head_r = st.columns([3, 1.2], gap="small")
    with head_l:
        section_header(5, "결과 확인")
    with head_r:
        locale = st.radio(
            "언어",
            ["ko", "en"],
            index=0 if st.session_state.get("result_locale", "ko") == "ko" else 1,
            format_func=lambda x: {"ko": "한국어", "en": "English"}[x],
            horizontal=True,
            key="result_locale_radio",
            label_visibility="collapsed",
        )
    st.session_state.result_locale = locale

    rail_col, preview_col, edit_col = st.columns([1, 2.4, 1.4], gap="medium")

    with rail_col:
        with st.container(border=True):
            panel_title("페이지")
            _thumb_rail(locale)

    with preview_col:
        _preview(locale)

    with edit_col:
        _edit_panel(locale)

    _action_bar(client)

    if st.session_state.card_review_approved:
        st.caption(
            f"검토 승인 완료 — 남은 재생성: {st.session_state.card_revisions_remaining}회"
        )
