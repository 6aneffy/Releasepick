"""MOFE 공식 보도자료 RSS + 상세 페이지 첨부 메타 수집.

운영 흐름:
1. RSS 에서 최근 N 건의 (제목, 링크, nttId, 발행일, 작성자) 메타 수집
2. 각 상세 페이지를 GET 해서 첨부파일 목록 파싱
3. 첨부 우선순위 PDF > HWPX > HWP. HWP 만 있는 게시물은 호출부에서 비활성화 처리

가이드 (01_크롤링_간단가이드.md) 준수:
- 요청 사이 0.6s sleep
- UA 헤더 명시
- UTF-8 안전 처리

mofe.go.kr 특이사항:
- RSS link 는 http:// 로 시작. http 로 GET 하면 상세가 아니라 homepage list 가
  돌아온다 → HTTPS 로 강제 변환 필요.
- 첨부 다운로드 endpoint: /com/cmm/fms/FileDown.do?atchFileId=...&fileSn=N
- AtchZipFileDown.do (전체 압축) 과 synapView.do (뷰어) 는 무시.
"""

from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Iterable, Tuple
from urllib.parse import urljoin, urlsplit

import requests
import streamlit as st
from bs4 import BeautifulSoup


RSS_URL = (
    "https://www.mofe.go.kr/com/detailRssTagService.do"
    "?bbsId=MOSFBBS_000000000028"
)
BASE_URL = "https://www.mofe.go.kr"

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
_HEADERS = {
    "User-Agent": _UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}
_TIMEOUT = 15
_SLEEP = 0.6

_LABEL_TAIL_RE = re.compile(
    r"\s*(다운로드|미리보기|바로보기|새창|새창열림|아이콘)\s*$"
)
_WS_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class PressItem:
    title: str
    link: str
    ntt_id: str
    pub_date: str
    author: str


@dataclass(frozen=True)
class Attachment:
    filename: str
    url: str
    ext: str  # "pdf" / "hwpx" / "hwp" / "etc"


class PressFetchError(RuntimeError):
    pass


def _normalize_link(link: str) -> str:
    """HTTP → HTTPS 변환. RSS 가 http:// 를 주는데 그대로 GET 하면
    서버가 detail 페이지 대신 homepage list 를 반환한다."""
    if link.startswith("http://www.mofe.go.kr"):
        link = "https://" + link[len("http://") :]
    return link


def _ext_of(name: str) -> str:
    n = name.lower().strip()
    if n.endswith(".pdf"):
        return "pdf"
    if n.endswith(".hwpx"):
        return "hwpx"
    if n.endswith(".hwp"):
        return "hwp"
    return "etc"


@st.cache_data(ttl=600, show_spinner=False)
def fetch_recent_items(limit: int = 5) -> list[PressItem]:
    """RSS 2.0 파싱. item 필드: title, link, tag(=nttId), pubDate, author."""
    resp = requests.get(RSS_URL, headers=_HEADERS, timeout=_TIMEOUT)
    if resp.status_code != 200:
        raise PressFetchError(f"RSS HTTP {resp.status_code}")
    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as exc:
        raise PressFetchError(f"RSS XML 파싱 실패: {exc}") from exc

    items: list[PressItem] = []
    for item in root.iter("item"):
        if len(items) >= limit:
            break
        title = (item.findtext("title") or "").strip()
        link = _normalize_link((item.findtext("link") or "").strip())
        ntt_id = (item.findtext("tag") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        author = (item.findtext("author") or "").strip()
        if not (title and link and ntt_id):
            continue
        items.append(
            PressItem(
                title=title,
                link=link,
                ntt_id=ntt_id,
                pub_date=pub_date,
                author=author,
            )
        )
    return items


def _detail_html(detail_url: str) -> str:
    resp = requests.get(detail_url, headers=_HEADERS, timeout=_TIMEOUT)
    if resp.status_code != 200:
        raise PressFetchError(f"상세 HTTP {resp.status_code}")
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


def _clean_name(raw: str) -> str:
    s = _WS_RE.sub(" ", raw).replace("\xa0", " ").strip()
    s = _LABEL_TAIL_RE.sub("", s).strip()
    return s


@st.cache_data(ttl=600, show_spinner=False)
def fetch_attachments(detail_url: str) -> list[Attachment]:
    """상세 페이지 → BeautifulSoup → 첨부 파일명·다운로드 URL 추출.

    필터:
    - FileDown.do 만. AtchZipFileDown (전체 압축) 과 synapView (뷰어) 제외
    - anchor text 에서 라벨 꼬리 ("다운로드 아이콘" 등) 제거
    - 확장자 미상 (etc) 항목 제외 — 같은 URL 의 다른 anchor 에 실제 파일명이 있음
    - URL 단위 중복 제거 (같은 fileSn 의 이름 + 아이콘 anchor 두 개 → 하나만)
    """
    html = _detail_html(detail_url)
    soup = BeautifulSoup(html, "html.parser")
    seen_urls: set[str] = set()
    out: list[Attachment] = []
    for a in soup.find_all("a"):
        href = a.get("href") or ""
        if not href:
            continue
        if "FileDown.do" not in href or "AtchZipFileDown" in href:
            continue
        name = _clean_name(a.get_text(" ", strip=True) or "")
        ext = _ext_of(name)
        if ext == "etc":
            continue
        url = urljoin(BASE_URL, href)
        if url in seen_urls:
            continue
        seen_urls.add(url)
        out.append(Attachment(filename=name, url=url, ext=ext))
    return out


_PRIORITY = ("pdf", "hwpx", "hwp")


def pick_best_attachment(attachments: Iterable[Attachment]) -> Attachment | None:
    """PDF > HWPX > HWP 순. HWP 만 있으면 None 반환 (호출부에서 비활성)."""
    bucket: dict[str, Attachment] = {}
    for att in attachments:
        if att.ext in _PRIORITY and att.ext not in bucket:
            bucket[att.ext] = att
    if "pdf" in bucket:
        return bucket["pdf"]
    if "hwpx" in bucket:
        return bucket["hwpx"]
    return None


@st.cache_data(ttl=600, show_spinner=False)
def fetch_items_with_attachments(
    limit: int = 5,
) -> list[Tuple[PressItem, list[Attachment]]]:
    """RSS + 각 상세 페이지 → 한 번에 카드 그릴 메타 모두 반환."""
    items = fetch_recent_items(limit=limit)
    out: list[Tuple[PressItem, list[Attachment]]] = []
    for i, item in enumerate(items):
        if i > 0:
            time.sleep(_SLEEP)
        try:
            atts = fetch_attachments(item.link)
        except PressFetchError:
            atts = []
        out.append((item, atts))
    return out


def download_attachment(url: str) -> bytes:
    """첨부 바이너리 다운로드. Referer 부착 (일부 정부 사이트는 요구)."""
    parsed = urlsplit(url)
    referer = f"{parsed.scheme}://{parsed.netloc}/"
    headers = {**_HEADERS, "Referer": referer}
    resp = requests.get(url, headers=headers, timeout=30, stream=True)
    if resp.status_code != 200:
        raise PressFetchError(f"첨부 다운로드 HTTP {resp.status_code}")
    return resp.content
