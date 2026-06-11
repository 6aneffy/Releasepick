"""1페이지 / 2~5+페이지 디자인 컨셉 카탈로그 (themes/template1·template2 가이드)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent
ROOT9 = CODE_DIR.parent
GUIDE_1PAGE = ROOT9 / "themes" / "template1" / "템플릿-1.txt"
GUIDE_MULTIPAGE = ROOT9 / "themes" / "template2" / "# Multi-Page Card News (2~5 Pages).txt"


@dataclass(frozen=True)
class TemplateConcept:
    id: str
    group: str  # "1page" | "multipage"
    index: int
    title_ko: str
    subtitle_ko: str
    use_cases: tuple[str, ...]
    thumbnail_prompt: str
    plan_style_block: str
    image_style_block: str


ONE_PAGE_CONCEPTS: tuple[TemplateConcept, ...] = (
    TemplateConcept(
        id="1p_poster",
        group="1page",
        index=1,
        title_ko="포스터형",
        subtitle_ko="모집공고 · 행사안내 · 정책공지",
        use_cases=("모집 공고", "신청 안내", "행사 안내", "공모전"),
        thumbnail_prompt=(
            "Clean Korean government recruitment poster style preview. Strong headline area at top, "
            "simple calendar and contact icons, trustworthy public notice layout, soft blue and white, "
            "minimal flat illustration, no readable text, no logos."
        ),
        plan_style_block=(
            "[선택 컨셉: ① 포스터형]\n"
            "1장 카드뉴스를 공공기관 포스터·모집공고 스타일로 기획한다. "
            "강한 헤드라인, 신청기간·대상·문의처·CTA를 명확히. 인포그래픽보다 공고문 톤."
        ),
        image_style_block=(
            "[디자인 컨셉 — 포스터형]\n"
            "Government public notice poster: bold headline hierarchy, application deadline and contact cues, "
            "clean official layout, trustworthy blue-white palette, concise CTA band."
        ),
    ),
    TemplateConcept(
        id="1p_infographic",
        group="1page",
        index=2,
        title_ko="1장 요약형",
        subtitle_ko="경제지표 · 통계 · 정책성과",
        use_cases=("GDP", "물가", "신용등급", "수출입", "예산"),
        thumbnail_prompt=(
            "Economic infographic summary card preview. Large numeric highlights, simple bar and line chart icons, "
            "data visualization blocks, pastel blue and green, clean white background, no readable text, no logos."
        ),
        plan_style_block=(
            "[선택 컨셉: ② 1장 요약형]\n"
            "1장 카드뉴스를 숫자·지표 중심 인포그래픽으로 기획한다. "
            "핵심 수치, 비교·증감, 정책 의미·기대효과를 한 화면에 요약."
        ),
        image_style_block=(
            "[디자인 컨셉 — 1장 요약형]\n"
            "Infographic summary: prominent statistics, chart icons, comparison arrows, "
            "data-first layout, easy-to-scan numeric blocks."
        ),
    ),
    TemplateConcept(
        id="1p_typography",
        group="1page",
        index=3,
        title_ko="텍스트 강조형",
        subtitle_ko="신규정책 · 캠페인 · 정책홍보",
        use_cases=("정책 발표", "민생안정", "경제활력", "규제혁신"),
        thumbnail_prompt=(
            "Bold typography-focused policy campaign preview. Large abstract headline blocks (no real letters), "
            "vivid accent color bands, minimal supporting icons, SNS-friendly composition, no readable text, no logos."
        ),
        plan_style_block=(
            "[선택 컨셉: ③ 텍스트 강조형]\n"
            "1장 카드뉴스를 타이포그래피·메시지 중심 캠페인으로 기획한다. "
            "짧은 보조 설명과 강한 헤드카피, 이미지보다 문장 임팩트 우선."
        ),
        image_style_block=(
            "[디자인 컨셉 — 텍스트 강조형]\n"
            "Typography-first campaign: oversized title treatment, strong color accents, "
            "message-driven layout optimized for social sharing."
        ),
    ),
)

MULTI_PAGE_CONCEPTS: tuple[TemplateConcept, ...] = (
    TemplateConcept(
        id="mp_economy",
        group="multipage",
        index=1,
        title_ko="종합경제정책 및 성장",
        subtitle_ko="경제정책 · 성장전략 · 산업·수출",
        use_cases=("경제정책", "성장전략", "수출", "기업지원", "혁신성장"),
        thumbnail_prompt=(
            "Clean flat vector illustration for government economic policy news card. "
            "Professional office environment with upward growth charts, glowing light bulb representing innovation, "
            "connected gears symbolizing economic systems and policy execution. Corporate blue and pastel green color palette, "
            "minimalist composition, clean white background, trustworthy government communication style, "
            "modern infographic elements, high resolution, social media card design, no text, no photorealism, "
            "no 3D rendering, no complex details."
        ),
        plan_style_block=(
            "[선택 컨셉: ① 종합경제정책 및 성장]\n"
            "표지·본문 톤을 경제성장·산업·수출·투자·혁신 정책에 맞춘다. "
            "표지: 성장·신뢰. 본문: 인포그래픽·수치 시각화·경제 지표 강조."
        ),
        image_style_block=(
            "[디자인 컨셉 — 종합경제정책 및 성장]\n"
            "Growth and innovation: upward charts, economic icons, corporate-friendly trust, "
            "blue-green palette, infographic-friendly body pages."
        ),
    ),
    TemplateConcept(
        id="mp_welfare",
        group="multipage",
        index=2,
        title_ko="세금 및 복지혜택",
        subtitle_ko="세제혜택 · 환급 · 민생지원",
        use_cases=("세금", "공제", "환급", "복지", "장려금", "바우처"),
        thumbnail_prompt=(
            "Minimal isometric illustration representing tax benefits and financial welfare. "
            "Modern piggy bank, smartphone displaying transfer confirmation and check marks, "
            "organized document folders and benefit icons. Friendly yet trustworthy design, "
            "warm yellow and professional navy palette, clean layout, government information card style, "
            "social media optimized composition, high resolution, no text, no photorealistic objects, "
            "no 3D rendering, simple geometric illustration."
        ),
        plan_style_block=(
            "[선택 컨셉: ② 세금 및 복지혜택]\n"
            "표지·본문을 세제·복지·지원금·생활밀착 혜택 안내에 맞춘다. "
            "대상자·신청절차·혜택 요약이 읽기 쉽게."
        ),
        image_style_block=(
            "[디자인 컨셉 — 세금 및 복지혜택]\n"
            "Benefits and welfare: support icons, friendly navy-yellow palette, "
            "lifestyle-close imagery, clear eligibility and application flow."
        ),
    ),
    TemplateConcept(
        id="mp_future",
        group="multipage",
        index=3,
        title_ko="미래경제 및 친환경",
        subtitle_ko="AI · 디지털 · 탄소중립",
        use_cases=("AI", "디지털", "탄소중립", "ESG", "신재생에너지"),
        thumbnail_prompt=(
            "Modern flat vector design for future economy and green innovation policy. "
            "Smart city skyline with wind turbines, solar panels, digital network connections and sustainable technology elements. "
            "Tech blue and eco green color palette, optimistic and forward-looking atmosphere, clean light gray background, "
            "government innovation campaign style, minimalist composition, high resolution, no text, "
            "no photorealistic imagery, no 3D rendering."
        ),
        plan_style_block=(
            "[선택 컨셉: ③ 미래경제 및 친환경]\n"
            "표지·본문을 미래산업·AI·디지털·탄소중립·친환경 정책에 맞춘다. "
            "혁신·지속가능성·기술 이미지를 활용."
        ),
        image_style_block=(
            "[디자인 컨셉 — 미래경제 및 친환경]\n"
            "Future and green innovation: smart city, digital networks, renewable energy, "
            "tech blue and eco green, forward-looking campaign tone."
        ),
    ),
)

_ALL: dict[str, TemplateConcept] = {
    c.id: c for c in (*ONE_PAGE_CONCEPTS, *MULTI_PAGE_CONCEPTS)
}

# 가이드 문서 키워드 (자동 추천)
_1P_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("1p_poster", ("모집", "신청", "접수", "공고", "설명회", "공모", "행사")),
    ("1p_infographic", ("gdp", "물가", "신용등급", "수출", "수입", "예산", "통계", "지표", "%", "성장률")),
    ("1p_typography", ("새로운 정책", "정책 발표", "민생안정", "경제활력", "혁신", "캠페인", "비전")),
]

_MP_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("mp_economy", ("경제정책", "성장", "산업", "수출", "투자", "기업", "경제활력", "혁신성장", "경쟁력")),
    ("mp_welfare", ("세금", "세제", "감면", "공제", "환급", "복지", "지원금", "장려금", "바우처", "청년", "서민")),
    ("mp_future", ("ai", "디지털", "탄소", "esg", "친환경", "신재생", "미래", "그린", "기술")),
]


def page_group(target_pages: int) -> str:
    return "1page" if target_pages == 1 else "multipage"


def concepts_for_pages(target_pages: int) -> tuple[TemplateConcept, ...]:
    return ONE_PAGE_CONCEPTS if target_pages == 1 else MULTI_PAGE_CONCEPTS


def get_concept(concept_id: str | None) -> TemplateConcept | None:
    if not concept_id:
        return None
    return _ALL.get(concept_id)


def recommend_concept_id(press_text: str, target_pages: int) -> str:
    """보도자료 키워드로 추천 컨셉 ID (가이드 자동 분류 규칙)."""
    text = press_text.lower()
    keywords = _1P_KEYWORDS if target_pages == 1 else _MP_KEYWORDS
    defaults = ("1p_poster", "mp_economy")
    default = defaults[0] if target_pages == 1 else defaults[1]
    best_id = default
    best_score = 0
    for cid, kws in keywords:
        score = sum(1 for kw in kws if kw in text or kw.lower() in text)
        if score > best_score:
            best_score = score
            best_id = cid
    return best_id


def load_one_page_template_text() -> str:
    try:
        return GUIDE_1PAGE.read_text(encoding="utf-8")
    except OSError:
        return ""


def load_guide_excerpt(target_pages: int, max_chars: int = 4000) -> str:
    path = GUIDE_1PAGE if target_pages == 1 else GUIDE_MULTIPAGE
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    if len(text) <= max_chars:
        return text
    return text[: max_chars // 2] + "\n...[생략]...\n" + text[-max_chars // 2 :]


def concept_plan_block(concept_id: str | None) -> str:
    c = get_concept(concept_id)
    if not c:
        return ""
    guide = load_guide_excerpt(1 if c.group == "1page" else 2, max_chars=2000)
    return f"{c.plan_style_block}\n\n[컨셉 가이드 발췌]\n{guide[:1500]}"


def concept_image_block(concept_id: str | None) -> str:
    c = get_concept(concept_id)
    return c.image_style_block if c else ""
