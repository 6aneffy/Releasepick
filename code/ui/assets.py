"""Static asset helpers (logo + hero mock images as data URIs)."""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st


CODE_DIR = Path(__file__).resolve().parents[1]
ROOT = CODE_DIR.parent
LOGO_PATH = ROOT / "logo.png"


def _file_data_uri(path: Path, mime: str) -> str:
    if not path.is_file():
        return ""
    raw = path.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}"


@st.cache_resource(show_spinner=False)
def logo_data_uri() -> str:
    """Return base64 data URI for logo.png, or empty string if missing."""
    return _file_data_uri(LOGO_PATH, "image/png")


@st.cache_resource(show_spinner=False)
def hero_mock_data_uris() -> list[str]:
    """Return [01.jpg, 02.jpg, 03.jpg] as data URIs (empty if missing)."""
    return [
        _file_data_uri(ROOT / "01.jpg", "image/jpeg"),
        _file_data_uri(ROOT / "02.jpg", "image/jpeg"),
        _file_data_uri(ROOT / "03.jpg", "image/jpeg"),
    ]
