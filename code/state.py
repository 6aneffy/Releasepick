"""Session state helpers shared across views."""

from __future__ import annotations

import json
import uuid

import streamlit as st

import job_store
from content_filter import ContentFilterError, assert_plan_safe


SESSION_DEFAULTS: dict = {
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
    "concept_template_id": None,
    "concept_confirmed": False,
    "concept_thumb_paths": {},
    "target_pages_group": None,
    "multipage_variant": "v1",
    "cover_variants": {},
    "selected_variant": None,
    "editor_step": 1,
    "result_locale": "ko",
    "result_active_idx": 0,
    "press_items_payload": [],
    "press_items_fetched_at": None,
    "selected_press_ntt_id": None,
    "selected_attachment_name": "",
    "selected_attachment_ext": "",
    "instagram_caption": "",
    "instagram_uploaded_post_id": None,
    "instagram_uploaded_keys": [],
    "instagram_cleanup_done": False,
    "_hydrated": False,
    "_seed_bump": -1,
}


def init_session() -> None:
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    for k, v in SESSION_DEFAULTS.items():
        st.session_state.setdefault(k, v)


def snapshot() -> dict:
    keys = [
        "plan_text",
        "plan_dict",
        "plan_phase",
        "plan_revisions_remaining",
        "plan_first_approved",
        "plan_bump",
        "card_review_approved",
        "card_revisions_remaining",
        "card_paths",
        "card_paths_en",
        "press_text",
        "pdf_name",
        "concept_template_id",
        "concept_confirmed",
        "editor_step",
        "target_pages",
        "multipage_variant",
        "cover_variants",
        "selected_variant",
        "press_items_payload",
        "press_items_fetched_at",
        "selected_press_ntt_id",
        "selected_attachment_name",
        "selected_attachment_ext",
        "instagram_caption",
        "instagram_uploaded_post_id",
        "instagram_uploaded_keys",
        "instagram_cleanup_done",
    ]
    return {k: st.session_state.get(k) for k in keys}


def persist() -> None:
    job_store.save_snapshot(st.session_state.session_id, snapshot())


def try_hydrate() -> None:
    if st.session_state.get("_hydrated"):
        return
    job_store.init_db()
    snap = job_store.load_snapshot(st.session_state.session_id)
    if snap:
        for k, v in snap.items():
            if k == "plan_dict" and v is None:
                continue
            st.session_state[k] = v
        if st.session_state.get("plan_dict") and not st.session_state.get("plan_text"):
            st.session_state.plan_text = json.dumps(
                st.session_state.plan_dict, ensure_ascii=False, indent=2
            )
        st.session_state._seed_bump = -1
    st.session_state._hydrated = True


def plan_to_text() -> None:
    if st.session_state.plan_dict:
        st.session_state.plan_text = json.dumps(
            st.session_state.plan_dict, ensure_ascii=False, indent=2
        )


def seed_page_widgets_from_plan() -> None:
    pd = st.session_state.plan_dict
    if not pd:
        return
    st.session_state.pg_series = pd.get("series_title", "")
    st.session_state.pg_head = pd.get("head_copy", "")
    for i, s in enumerate(pd.get("slides") or []):
        st.session_state[f"pg_{i}_title"] = s.get("title", "")
        st.session_state[f"pg_{i}_bullets"] = "\n".join(s.get("bullets") or [])
        st.session_state[f"pg_{i}_footnote"] = (s.get("footnote") or "") or ""


def widgets_into_plan_dict() -> None:
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
    plan_to_text()


def guard_plan(plan_d: dict | None, *, context: str) -> bool:
    if not plan_d:
        return False
    try:
        assert_plan_safe(plan_d)
    except ContentFilterError as exc:
        st.error(f"**{context}** — 정서·이미지 안전 필터\n\n{exc}")
        return False
    return True


def reset_session() -> None:
    sid = st.session_state.get("session_id")
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    if sid:
        st.session_state.session_id = sid
