from __future__ import annotations

import mimetypes
import os
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import requests

_TIMEOUT = 30


@dataclass(frozen=True)
class UploadedAsset:
    key: str
    url: str


class SupabaseStorageError(RuntimeError):
    pass


def _config() -> tuple[str, str, str]:
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    bucket = os.getenv("SUPABASE_BUCKET", "")
    if not (url and key and bucket):
        raise SupabaseStorageError(
            "Supabase env 누락: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / SUPABASE_BUCKET"
        )
    return url, key, bucket


def _headers(service_key: str, *, content_type: str | None = None) -> dict[str, str]:
    h = {
        "Authorization": f"Bearer {service_key}",
        "apikey": service_key,
    }
    if content_type:
        h["Content-Type"] = content_type
        h["x-upsert"] = "true"
    return h


def _encode_key(key: str) -> str:
    return "/".join(quote(part, safe="") for part in key.split("/"))


def _guess_content_type(path: Path) -> str:
    ct, _ = mimetypes.guess_type(path.name)
    return ct or "application/octet-stream"


def upload_card_images(local_paths: list[Path], session_id: str) -> list[UploadedAsset]:
    base_url, service_key, bucket = _config()
    ts = int(time.time())
    assets: list[UploadedAsset] = []
    for p in local_paths:
        if not p.is_file():
            raise SupabaseStorageError(f"파일 없음: {p}")
        key = f"posts/{session_id}/{ts}/{p.name}"
        encoded = _encode_key(key)
        upload_url = f"{base_url}/storage/v1/object/{bucket}/{encoded}"
        try:
            with p.open("rb") as f:
                resp = requests.post(
                    upload_url,
                    data=f.read(),
                    headers=_headers(service_key, content_type=_guess_content_type(p)),
                    timeout=_TIMEOUT,
                )
        except requests.RequestException as exc:
            raise SupabaseStorageError(
                f"Supabase 연결 실패 ({base_url}): {exc}"
            ) from exc
        if resp.status_code >= 300:
            raise SupabaseStorageError(
                f"업로드 실패 {p.name}: {resp.status_code} {resp.text}"
            )
        public_url = get_url(key)
        assets.append(UploadedAsset(key=key, url=public_url))
    return assets


def get_url(key: str, expires_sec: int = 3600) -> str:
    base_url, service_key, bucket = _config()
    encoded = _encode_key(key)
    sign_url = f"{base_url}/storage/v1/object/sign/{bucket}/{encoded}"
    try:
        resp = requests.post(
            sign_url,
            json={"expiresIn": expires_sec},
            headers=_headers(service_key, content_type="application/json"),
            timeout=_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise SupabaseStorageError(
            f"Supabase 연결 실패 ({base_url}): {exc}"
        ) from exc
    if resp.status_code < 300:
        data = resp.json()
        signed_path = data.get("signedURL") or data.get("signedUrl")
        if signed_path:
            if signed_path.startswith("http"):
                return signed_path
            if not signed_path.startswith("/"):
                signed_path = "/" + signed_path
            return f"{base_url}/storage/v1{signed_path}" if not signed_path.startswith("/storage/") else f"{base_url}{signed_path}"
    return f"{base_url}/storage/v1/object/public/{bucket}/{encoded}"


def delete_objects(keys: list[str]) -> None:
    if not keys:
        return
    base_url, service_key, bucket = _config()
    resp = requests.delete(
        f"{base_url}/storage/v1/object/{bucket}",
        json={"prefixes": list(keys)},
        headers=_headers(service_key, content_type="application/json"),
        timeout=_TIMEOUT,
    )
    if resp.status_code >= 300:
        raise SupabaseStorageError(
            f"삭제 실패: {resp.status_code} {resp.text}"
        )
