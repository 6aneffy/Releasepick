"""HWPX (.hwpx) → 본문 텍스트 추출.

HWPX 는 ZIP + XML (OWPML) 구조이다. `Contents/section*.xml` 안의
네임스페이스 `hp:` 의 `<t>` 요소가 실제 본문 텍스트이다.

표준 라이브러리만 사용 (zipfile, xml.etree.ElementTree).
"""

from __future__ import annotations

import io
import zipfile
import xml.etree.ElementTree as ET


class HwpxExtractError(RuntimeError):
    pass


def _is_section_xml(name: str) -> bool:
    low = name.lower()
    return (
        low.startswith("contents/section")
        and low.endswith(".xml")
    )


def _iter_text_elements(root: ET.Element):
    """tag 가 `}t` 로 끝나거나 정확히 `t` 인 모든 요소 yield."""
    for el in root.iter():
        tag = el.tag if isinstance(el.tag, str) else ""
        if tag == "t" or tag.endswith("}t"):
            yield el


def extract_text_from_hwpx_bytes(raw: bytes) -> str:
    """HWPX 바이너리 → 평문 텍스트. 실패 시 HwpxExtractError."""
    if not raw:
        raise HwpxExtractError("빈 입력")
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as exc:
        raise HwpxExtractError(f"HWPX 가 올바른 ZIP 이 아님: {exc}") from exc

    chunks: list[str] = []
    with zf:
        section_names = sorted(n for n in zf.namelist() if _is_section_xml(n))
        if not section_names:
            raise HwpxExtractError("Contents/section*.xml 없음 — 유효한 HWPX 아님")
        for n in section_names:
            try:
                root = ET.fromstring(zf.read(n))
            except ET.ParseError:
                # 한 섹션이 깨졌어도 다른 섹션은 시도
                continue
            for el in _iter_text_elements(root):
                if el.text:
                    chunks.append(el.text)
            chunks.append("\n")
    text = "".join(chunks).strip()
    if not text:
        raise HwpxExtractError("HWPX 안에 텍스트 노드가 없음")
    return text
