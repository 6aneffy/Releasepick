"""Landing page (stitch _1): hero + bento feature grid."""

from __future__ import annotations

import streamlit as st

from ui.components import (
    feature_card,
    footer,
    hero_left_html,
    hero_right_html,
    top_app_bar,
)
from ui.theme import inject_global_css


def render() -> None:
    inject_global_css()
    nav = st.query_params.get("nav")
    if nav == "editor":
        st.query_params.clear()
        st.switch_page("views/editor.py")
    elif nav == "home":
        st.query_params.clear()
    top_app_bar(active="home")

    hero_l, hero_r = st.columns([1, 1.05], gap="medium")
    with hero_l:
        st.markdown(hero_left_html(), unsafe_allow_html=True)
        if st.button(
            "보도자료 업로드하고 시작하기  →",
            type="primary",
            key="hero_upload_btn",
        ):
            st.session_state.editor_step = 1
            st.switch_page("views/editor.py")
    with hero_r:
        st.markdown(hero_right_html(), unsafe_allow_html=True)

    st.markdown(
        """
        <div class="rp-section-band">
          <div class="rp-section-eyebrow">
            <span class="material-symbols-outlined" style="font-size:14px">bolt</span>
            CORE FEATURES
          </div>
          <div class="rp-section-h">기획부터 디자인까지, 한 흐름으로</div>
          <div class="rp-section-sub">
            AI가 보도자료를 분석해 카드뉴스 초안과 디자인을 자동 생성합니다.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    f1, f2, f3 = st.columns(3, gap="medium")
    with f1:
        feature_card(
            "analytics",
            "보도자료 핵심 추출",
            "AI가 수십 페이지의 보도자료를 빠르게 분석하여 가장 중요한 핵심 키워드와 문장을 선별합니다.",
        )
    with f2:
        feature_card(
            "auto_stories",
            "카드뉴스 문안 자동 구성",
            "추출된 정보를 바탕으로 카드뉴스 형식에 최적화된 짧고 강렬한 카피라이팅을 자동으로 제안합니다.",
        )
    with f3:
        feature_card(
            "palette",
            "표지·본문 디자인 자동 생성",
            "재정경제부 표준 가이드라인을 준수하는 템플릿에 맞춤형 이미지를 결합해 완성본을 제공합니다.",
        )

    footer()


render()
