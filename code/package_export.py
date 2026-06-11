"""Assemble final ZIP: PPTX plan + jpeg/*.jpg"""

from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path

from export_plan_pptx import build_plan_pptx_bytes
from models import CardNewsPlan


def build_export_zip_bytes(
    plan_dict: dict,
    jpeg_paths: list[Path],
    *,
    cards_root: Path | None = None,
) -> bytes:
    plan = CardNewsPlan.model_validate(plan_dict)
    pptx_bytes = build_plan_pptx_bytes(plan)
    bio = BytesIO()
    root_resolved = cards_root.resolve() if cards_root else None
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("기획안_최종.pptx", pptx_bytes)
        for p in jpeg_paths:
            if not p.exists():
                continue
            pr = p.resolve()
            if root_resolved is not None:
                try:
                    rel = pr.relative_to(root_resolved).as_posix()
                except ValueError:
                    rel = p.name
                arc = f"jpeg/{rel}"
            else:
                arc = f"jpeg/{p.name}"
            zf.write(p, arcname=arc)
    return bio.getvalue()
