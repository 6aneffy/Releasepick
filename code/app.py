"""릴리즈픽 — 카드뉴스 제작 (Streamlit, multipage shell).

`code/app.py` is a thin router. All business logic lives in `views/` and
`state.py`, all styling in `ui/`.
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="재정경제부 AI 카드뉴스 제작지원",
    page_icon="🪪",
    layout="wide",
    initial_sidebar_state="collapsed",
)

landing_page = st.Page(
    "views/landing.py",
    title="홈",
    icon=":material/home:",
    default=True,
    url_path="home",
)
editor_page = st.Page(
    "views/editor.py",
    title="카드뉴스 제작",
    icon=":material/auto_stories:",
    url_path="editor",
)

nav = st.navigation([landing_page, editor_page], position="hidden")
nav.run()
