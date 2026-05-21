"""국장님믿고갑조 템플릿 원문 로드 (표지 / 본문)."""

from __future__ import annotations

from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent
ROOT9 = CODE_DIR.parent
COVER_TEMPLATE_PATH = ROOT9 / "국장님믿고갑조" / "템플릿(표지).txt"
BODY_TEMPLATE_PATH = ROOT9 / "국장님믿고갑조" / "템플릿(본문).txt"
ENGLISH_LOGO_PATH = ROOT9 / "국장님믿고갑조" / "재정경제부 영문로고 파일.png"


def load_cover_template_text() -> str:
    try:
        return COVER_TEMPLATE_PATH.read_text(encoding="utf-8")
    except OSError:
        return ""


def load_body_template_text() -> str:
    try:
        return BODY_TEMPLATE_PATH.read_text(encoding="utf-8")
    except OSError:
        return ""


def load_english_logo_bytes() -> bytes | None:
    """영문 카드뉴스 합성용 재정경제부 영문 로고 PNG."""
    try:
        return ENGLISH_LOGO_PATH.read_bytes()
    except OSError:
        return None
