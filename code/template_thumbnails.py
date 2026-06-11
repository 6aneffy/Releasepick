"""디자인 컨셉 선택용 대략적 썸네일 생성."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from template_catalog import TemplateConcept, concepts_for_pages

if TYPE_CHECKING:
    from openai import OpenAI

from image_gen import _decode_response

logger = logging.getLogger(__name__)

THUMBNAIL_MODEL = "gpt-image-1-mini"
THUMBNAIL_PREFIX = (
    "Rough style-preview thumbnail ONLY for UI template picker. "
    "NOT a finished card news page. No readable text, no ministry logos, no watermarks. "
)


def _thumbnail_prompt(concept: TemplateConcept) -> str:
    return THUMBNAIL_PREFIX + concept.thumbnail_prompt


def generate_concept_thumbnail(client: OpenAI, concept: TemplateConcept) -> bytes | None:
    """저해상도·저품질 컨셉 썸네일 1장."""
    prompt = _thumbnail_prompt(concept)[:8000]
    try:
        resp = client.images.generate(
            model=THUMBNAIL_MODEL,
            prompt=prompt,
            n=1,
            size="1024x1024",
            quality="low",
            output_format="png",
            moderation="auto",
        )
    except Exception as exc:
        logger.warning("Thumbnail API error (%s): %s", concept.id, exc)
        return None
    return _decode_response(resp)


def thumb_cache_dir(session_id: str) -> Path:
    from tempfile import gettempdir

    d = Path(gettempdir()) / "cardnews_concept_thumbs" / session_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def generate_thumbnails_for_pages(
    client: OpenAI,
    session_id: str,
    target_pages: int,
    *,
    progress_callback=None,
) -> dict[str, Path]:
    """페이지 수에 맞는 3종 썸네일 생성. concept_id → PNG 경로."""
    out: dict[str, Path] = {}
    concepts = concepts_for_pages(target_pages)
    cache = thumb_cache_dir(session_id)
    for i, concept in enumerate(concepts):
        dest = cache / f"{concept.id}.png"
        if dest.is_file() and dest.stat().st_size > 1000:
            out[concept.id] = dest
            if progress_callback:
                progress_callback(i + 1, len(concepts))
            continue
        png = generate_concept_thumbnail(client, concept)
        if png:
            dest.write_bytes(png)
            out[concept.id] = dest
        if progress_callback:
            progress_callback(i + 1, len(concepts))
    return out
