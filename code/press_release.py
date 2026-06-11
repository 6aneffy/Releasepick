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
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
}
_TIMEOUT = 20
_SLEEP = 0.8
_MAX_RETRIES = 3
_RETRY_BACKOFF = (1.5, 3.0, 6.0)


def _make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(_HEADERS)
    return s


def _get(session: requests.Session, url: str, *, stream: bool = False) -> requests.Response:
    """ConnectionReset 등 일시 오류는 백오프 재시도."""
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            return session.get(url, timeout=_TIMEOUT, stream=stream)
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_BACKOFF[attempt])
    raise PressFetchError(
        f"네트워크 오류 (재시도 {_MAX_RETRIES}회 실패): {last_exc}"
    )

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
    sess = _make_session()
    resp = _get(sess, RSS_URL)
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


def _detail_html(detail_url: str, session: requests.Session | None = None) -> str:
    sess = session if session is not None else _make_session()
    resp = _get(sess, detail_url)
    if resp.status_code != 200:
        raise PressFetchError(f"상세 HTTP {resp.status_code}")
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


def _clean_name(raw: str) -> str:
    s = _WS_RE.sub(" ", raw).replace("\xa0", " ").strip()
    s = _LABEL_TAIL_RE.sub("", s).strip()
    return s


def _parse_attachments_from_html(html: str) -> list[Attachment]:
    """HTML 만 받아 첨부 메타 추출. 필터:
    - FileDown.do 만. AtchZipFileDown / synapView 제외
    - anchor text 라벨 꼬리 제거
    - 확장자 미상 (etc) 항목 제외
    - URL 단위 중복 제거
    """
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


@st.cache_data(ttl=600, show_spinner=False)
def fetch_attachments(detail_url: str) -> list[Attachment]:
    """상세 페이지 GET → 첨부 메타 추출. (개별 호출용 — 일반적으로
    `fetch_items_with_attachments` 가 단일 세션으로 묶어 호출함.)"""
    return _parse_attachments_from_html(_detail_html(detail_url))


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
    """RSS + 각 상세 페이지 → 한 번에 카드 그릴 메타 모두 반환.

    모든 요청은 단일 Session 으로 진행 (keep-alive · 쿠키 유지).
    """
    sess = _make_session()
    # RSS
    resp = _get(sess, RSS_URL)
    if resp.status_code != 200:
        raise PressFetchError(f"RSS HTTP {resp.status_code}")
    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as exc:
        raise PressFetchError(f"RSS XML 파싱 실패: {exc}") from exc

    items: list[PressItem] = []
    for el in root.iter("item"):
        if len(items) >= limit:
            break
        title = (el.findtext("title") or "").strip()
        link = _normalize_link((el.findtext("link") or "").strip())
        ntt_id = (el.findtext("tag") or "").strip()
        pub_date = (el.findtext("pubDate") or "").strip()
        author = (el.findtext("author") or "").strip()
        if not (title and link and ntt_id):
            continue
        items.append(
            PressItem(
                title=title, link=link, ntt_id=ntt_id,
                pub_date=pub_date, author=author,
            )
        )

    out: list[Tuple[PressItem, list[Attachment]]] = []
    for i, item in enumerate(items):
        if i > 0:
            time.sleep(_SLEEP)
        try:
            html = _detail_html(item.link, session=sess)
            atts = _parse_attachments_from_html(html)
        except PressFetchError:
            atts = []
        out.append((item, atts))
    return out


def download_attachment(url: str) -> bytes:
    """첨부 바이너리 다운로드. Referer 부착 + 재시도."""
    parsed = urlsplit(url)
    referer = f"{parsed.scheme}://{parsed.netloc}/"
    sess = _make_session()
    sess.headers["Referer"] = referer
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            resp = sess.get(url, timeout=60, stream=True)
            if resp.status_code != 200:
                raise PressFetchError(f"첨부 다운로드 HTTP {resp.status_code}")
            return resp.content
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_BACKOFF[attempt])
    raise PressFetchError(
        f"첨부 다운로드 실패 (재시도 {_MAX_RETRIES}회): {last_exc}"
    )
