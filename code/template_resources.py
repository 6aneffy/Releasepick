"""국장님믿고갑조 템플릿 원문 로드 (표지 / 본문)."""

from __future__ import annotations

from pathlib import Path

from english_logo import load_english_logo_bytes as _load_english_logo_bytes

CODE_DIR = Path(__file__).resolve().parent
ROOT9 = CODE_DIR.parent
COVER_TEMPLATE_PATH = ROOT9 / "국장님믿고갑조" / "템플릿(표지).txt"
BODY_TEMPLATE_PATH = ROOT9 / "국장님믿고갑조" / "템플릿(본문).txt"


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


def load_english_logo_bytes(
    ko_logo_path: Path | None = None,
    *,
    ko_logo_bytes: bytes | None = None,
) -> bytes | None:
    """영문 카드뉴스 합성용 — `logo.png` 엠블럼 + Ministry of Finance and Economy (구 영문 PNG 미사용)."""
    return _load_english_logo_bytes(ko_logo_path, ko_logo_bytes=ko_logo_bytes)
