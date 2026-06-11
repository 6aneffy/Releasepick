"""Reusable UI building blocks (HTML + streamlit hybrid)."""

from __future__ import annotations

import html
from typing import Iterable

import streamlit as st

from ui.assets import hero_mock_data_uris, logo_data_uri


EDITOR_STEPS: list[tuple[int, str, str]] = [
    (1, "파일 업로드", "upload_file"),
    (2, "내용 분석", "search_insights"),
    (3, "디자인 설정", "palette"),
    (4, "이미지 생성", "auto_awesome"),
    (5, "결과 확인", "fact_check"),
    (6, "SNS 업로드", "share"),
]


def top_app_bar(active: str = "home") -> None:
    """Render sticky header with logo + nav buttons.

    `active` ∈ {"home", "editor"}.
    """
    uri = logo_data_uri()
    img = (
        f'<img src="{uri}" alt="재정경제부 로고"/>'
        if uri
        else '<span style="font-size:20px">🪪</span>'
    )
    st.markdown(
        '<div class="rp-topbar-marker"></div>',
        unsafe_allow_html=True,
    )
    brand_col, sp, home_col, edit_col = st.columns([4, 1, 0.7, 1.1], gap="small")
    with brand_col:
        st.markdown(
            f'<div class="rp-topbar__brand">{img}'
            '<span class="rp-brand-text">재정경제부 AI 카드뉴스 제작지원</span>'
            '</div>',
            unsafe_allow_html=True,
        )
    with home_col:
        if st.button(
            "홈",
            key=f"nav_home_{active}",
            use_container_width=True,
            type="primary" if active == "home" else "secondary",
        ):
            st.switch_page("views/landing.py")
    with edit_col:
        if st.button(
            "카드뉴스 제작",
            key=f"nav_editor_{active}",
            use_container_width=True,
            type="primary" if active == "editor" else "secondary",
        ):
            st.switch_page("views/editor.py")


def hero_left_html() -> str:
    """Left column inner HTML: marker + badge + title + desc."""
    return """
    <div class="rp-hero-left">
      <span class="rp-hero-marker"></span>
      <div class="rp-hero__badge">
        <span class="material-symbols-outlined" style="font-size:16px">auto_awesome</span>
        AI 기반 자동 제작 시스템
      </div>
      <div class="rp-hero__title">
        보도자료를 카드뉴스로,<br/>더 빠르고 정확하게
      </div>
      <div class="rp-hero__desc">
        정책자료의 핵심을 분석해 표지와 본문 카드뉴스 초안을 자동 생성합니다.<br/>
        복잡한 경제 지표도 한눈에 들어오는 디자인으로 변환하세요.
      </div>
    </div>
    """


def hero_right_html() -> str:
    """Right column inner HTML: mock cards (01.jpg / 02.jpg / 03.jpg)."""
    uris = hero_mock_data_uris()
    left = (
        f'<img src="{uris[0]}" alt="card 1"/>'
        if uris[0] else ""
    )
    right = (
        f'<img src="{uris[1]}" alt="card 2"/>'
        if uris[1] else ""
    )
    center = (
        f'<img src="{uris[2]}" alt="card 3"/>'
        if uris[2] else ""
    )
    return f"""
    <div class="rp-hero__mockwrap">
      <div class="rp-mock-card left">{left}</div>
      <div class="rp-mock-card right">{right}</div>
      <div class="rp-mock-card center">{center}</div>
    </div>
    """


def feature_card(icon: str, title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="rp-feature">
          <div class="rp-feature__icon">
            <span class="material-symbols-outlined">{icon}</span>
          </div>
          <div class="rp-feature__title">{title}</div>
          <div class="rp-feature__body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def step_nav(current: int, completed: Iterable[int] = ()) -> None:
    """Vertical step navigation. Read-only — step transitions live in workspace footer."""
    done = set(completed)
    rows = []
    for num, label, icon in EDITOR_STEPS:
        if num == current:
            cls = "rp-step active"
            shown_icon = icon
        elif num in done:
            cls = "rp-step done"
            shown_icon = "check_circle"
        else:
            cls = "rp-step"
            shown_icon = icon
        rows.append(
            f'<div class="{cls}">'
            f'<span class="material-symbols-outlined">{shown_icon}</span>'
            f"<span>{html.escape(label)}</span></div>"
        )
    st.markdown(
        f"""
        <div class="rp-stepnav">
          <div class="rp-stepnav__title">카드뉴스 생성 단계</div>
          <div class="rp-stepnav__sub">AI 어시스턴트가 제작을 돕습니다</div>
          {''.join(rows)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(num: int, title: str) -> None:
    st.markdown(
        f"""
        <div class="rp-section">
          <span class="rp-section__num">{num}</span>
          <span class="rp-section__title">{html.escape(title)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def panel_title(text: str) -> None:
    st.markdown(
        f'<div class="rp-panel__title">{html.escape(text)}</div>',
        unsafe_allow_html=True,
    )


def pill(text: str, tone: str = "info") -> str:
    """Return HTML for an inline pill (use inside st.markdown)."""
    safe_tone = tone if tone in ("info", "ok", "warn", "error") else "info"
    return f'<span class="rp-pill tone-{safe_tone}">{html.escape(text)}</span>'


def footer() -> None:
    st.markdown(
        """
        <div class="rp-footer">
          <div>
            <div style="color:var(--rp-on-surface);font-weight:600">재정경제부 AI 카드뉴스 제작지원</div>
            <div>© 2026 Ministry of Economy and Finance. All rights reserved.</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
