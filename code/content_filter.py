"""정서·이미지 안전 필터 — 카드뉴스 기획·프롬프트·산출 전 사전 차단."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# LLM 기획·번역 시스템에 주입
PLAN_EDITOR_SAFETY_RULES = """
[정서·이미지 안전 — 필수 준수]
- 일본 문화·전통·관광·음식·건축·애니·만화 스타일, 기모노, 도리이, 벚꽃·후지산, 히노마루·일장기, 스시·라멘 등 일본 연상 문구·소재를 넣지 말 것.
- 일제강점기·일본 식민지배·조선총독부·황민화·신사참배·친일·식민지 잔재(건축·지명·제도·신사 터·기념물 등) 관련 문구·소재를 넣지 말 것.
- 북한·평양·김정은·주체사상·북한 국기·군사 퍼레이드 등 북한 연상 문구·소재를 넣지 말 것.
- 분단·전쟁·침략·혐오·선동, 논란 국기·상징(일본·북한·전쟁기·식민기 등) 언급 금지.
- 보수·진보·좌우·이념 갈등, 젠더·세대·지역 갈등, 혐오·비하·차별 표현을 넣지 말 것.
- 문안·이미지 방향은 대한민국 공공 정책 홍보에 맞는 중립·신뢰·친화 톤만 사용.
- 보도자료에 해당 소재가 있어도 카드뉴스에서는 제외·일반화·대체 표현한다.
"""

# 이미지 API 프롬프트 말미에 항상 추가
IMAGE_VISUAL_SAFETY_BLOCK = """
[정서·시각 안전 — 절대 금지]
DO NOT depict or suggest: Japanese culture or tourism visuals (kimono, torii, cherry blossoms, Mount Fuji, rising sun / hinomaru flag, sushi/ramen stereotypes, anime/manga style, Japanese castles/temples as focal art); Japanese colonial era in Korea (1910–1945): Governor-General building aesthetics, Shinto shrine (jinja) architecture or worship scenes, colonial-era monuments, pro-Japan colonial propaganda imagery, comfort women statues as focal controversy art, forced labor / conscription imagery; colonial remnant buildings, signs, or nostalgic “retro Japanese occupation” styling; North Korea (DPRK flag, Pyongyang, military parades, missiles, portraits of Kim family, Juche symbols); war, invasion, hate, or divisive political symbols; controversial national flags used as hero imagery; political ideology conflict (conservative vs progressive camps, left-right fighting imagery); gender war or gender-role battle cartoons; generational conflict (MZ vs boomers insults); regional rivalry or map-based discrimination (Honam/Yeongnam feuds); hate speech, slurs, discriminatory gestures toward disability, foreigners, LGBT+, religion, or race.
ONLY use neutral Korean government policy card-news visuals: friendly generic Korean citizens, public servants, economy/welfare/technology metaphors, soft 3D clay-style icons without country-specific controversial cues. No foreign national flags except Republic of Korea government branding area if applicable.
"""

# (카테고리, 정규식, 사용자 메시지)
_SENSITIVE_PATTERNS: list[tuple[str, re.Pattern[str], str]] = []


def _compile_patterns() -> None:
    if _SENSITIVE_PATTERNS:
        return
    raw: list[tuple[str, str, str]] = [
        # 일본 연상
        (
            "japan_culture",
            r"일본|日본|재팬|japan(?:ese)?|nippon|tokyo|osaka|kyoto|fuji(?:yama)?|"
            r"kimono|torii|sakura|cherry\s+blossom|hinomaru|rising\s+sun|"
            r"기모노|도리이|벚꽃|후지산|히노마루|일장기|"
            r"스시|라멘|사무라이|닌자|애니메이션|애니풍|만화풍|"
            r"일본\s*(?:문화|전통|관광|음식|건축|스타일)",
            "일본 문화·관광·상징과 연관된 표현이 감지되었습니다.",
        ),
        # 북한 연상
        (
            "north_korea",
            r"북한|북조선|조선민주주의|평양|p'yongyang|pyongyang|"
            r"north\s*korea|dprk|democratic\s+people'?s\s+republic\s+of\s+korea|"
            r"juche|주체사상|김정은|김정일|김일성|"
            r"북한\s*(?:국기|정권|미사일|핵|군사)",
            "북한·분단 정치와 연관된 표현이 감지되었습니다.",
        ),
        # 일제강점기·식민지 잔재
        (
            "colonial_remnants",
            r"일제\s*(?:강점|시대|하|만|통치|잔재|식민)|"
            r"일본\s*(?:강점|식민|지배|통치|제국)|"
            r"식민지\s*(?:시대|배|통치|지|잔재|건축|유적)|"
            r"(?:강점|식민)\s*기|"
            r"조선총독부|총독부|총독(?:부|관|府)|"
            r"경술국치|국치\s*병합|을사(?:조약|늑약|보호조약)|"
            r"황민화|황국신민|신사참배|조국어찬양|"
            r"내선(?:일치|융합)|"
            r"신사(?:참배|터|철거|부활|건립|정책|배경|건물)|"
            r"(?<![가-힣])신사(?!업)(?=[\s,·.。/]|$)|"
            r"친일(?:파|단체|정권|프로파간다|세력)?|"
            r"(?:일제|식민지|일본)\s*잔재|"
            r"잔재\s*(?:문화|건축|규제|제도|철거|정비)|"
            r"식민지\s*(?:건축|건물|유적|지명)|"
            r"일본식\s*(?:건물|건축|가옥|주택)|"
            r"구국단|조선호텔|"
            r"강제(?:동원|징용)|징용(?:공|대)|"
            r"위안부\s*(?:동상|문제|합의|피해)|"
            r"소녀상|평화의\s*소녀상|"
            r"colonial\s*(?:korea|era|rule|remnant|legacy|architecture)|"
            r"japanese\s*(?:colonial|occupation|imperial|annexation|rule)|"
            r"governor[- ]general\s+of\s+korea|"
            r"annexation\s+of\s+korea|"
            r"shinto\s+shrine|yasukuni|"
            r"comfort\s+women\s*statue",
            "일제강점기·식민지 잔재·친일·신사 등 식민지배 연관 표현이 감지되었습니다.",
        ),
        # 정치 이념·좌우 갈등
        (
            "political_ideology",
            r"보수(?:\s+)?(?:당|진영|정당|외곽|노선|성향|정치)|"
            r"진보(?:\s+)?(?:당|진영|정당|노선|성향|정치)|"
            r"(?:좌|우)파(?:\s*진영|\s*정당|\s*성향)?|"
            r"극(?:좌|우)(?:\s*진영|\s*정당|\s*노선)?|"
            r"정치\s*이념|이념\s*(?:갈등|대립|논쟁)|"
            r"좌우\s*(?:갈등|대립|논쟁|진영)|"
            r"여야\s*(?:갈등|대립|싸움)|"
            r"(?:보수|진보)\s*(?:vs|대|와)\s*(?:보수|진보|진보|보수)|"
            r"conservative\s+vs\s+liberal|left[- ]wing\s+politic|right[- ]wing\s+politic|"
            r"political\s+ideology\s+conflict",
            "정치 이념·보수·진보·좌우 갈등 연관 표현이 감지되었습니다.",
        ),
        # 젠더 갈등
        (
            "gender_conflict",
            r"젠더\s*갈등|성별\s*갈등|남녀\s*(?:갈등|대립|전쟁)|"
            r"성차별\s*논쟁|성\s*갈등|"
            r"(?:반)?페미(?:니즘| vs| 논쟁)|"
            r"남초|여초|"
            r"gender\s*(?:war|conflict|battle)",
            "젠더·성별 갈등 연관 표현이 감지되었습니다.",
        ),
        # 세대 갈등
        (
            "generational_conflict",
            r"세대\s*(?:갈등|전쟁|대립|차별|혐오)|"
            r"MZ(?:세대)?\s*(?:vs|대립|갈등)|"
            r"(?:베이비\s*)?붐어\s*(?:세대\s*)?(?:vs|갈등)|"
            r"(?<![가-힣])꼰대(?=[\s,·.。/]|$)|"
            r"(?<![가-힣])적개(?=[\s,·.。/]|$)|"
            r"세대\s*전쟁|"
            r"generational\s*conflict|boomer\s+vs\s+gen\s*z",
            "세대 갈등·비하 연관 표현이 감지되었습니다.",
        ),
        # 지역 갈등
        (
            "regional_conflict",
            r"지역\s*(?:갈등|차별|비하|혐오|대립)|지역주의|"
            r"(?:호남|영남|전라(?:도)?|경상(?:도)?)\s*(?:비하|혐오|갈등|대립|색깔)|"
            r"수도권\s*갈등|지방\s*갈등|"
            r"regional\s*(?:conflict|discrimination|rivalry)",
            "지역 갈등·차별 연관 표현이 감지되었습니다.",
        ),
        # 혐오·비하 표현
        (
            "hate_speech",
            r"혐오\s*(?:표현|발언|단어|메시지|게시|내용|영상)|"
            r"(?:장애인|외국인|이주민|성소수자|특정\s*종교)\s*혐오|"
            r"인종차별|종교\s*혐오|"
            r"비하\s*(?:발언|표현|단어)|차별\s*(?:발언|표현)|"
            r"혐\s*한|"
            r"hate\s*speech|hateful\s*slur|discriminatory\s*slur",
            "혐오·비하·차별 표현이 감지되었습니다.",
        ),
        # 분쟁·논란 상징 (역사·전쟁)
        (
            "conflict_symbols",
            r"전쟁\s*(?:기념|배경|장면)|침략\s*(?:기|의|상)|"
            r"위안부|강제징용\s*(?:상|기)|"
            r"욱일기|전범\s*기|"
            r"genocide\s+imagery",
            "전쟁·침략·논란 상징과 연관된 표현이 감지되었습니다.",
        ),
        # 외국 국기·영토 논쟁 히어로
        (
            "foreign_flags_hero",
            r"(?:일본|북한|중국|대만|taiwan)\s*국기|"
            r"japanese\s+flag|north\s+korean\s+flag|"
            r"독도\s*(?:분쟁|표기\s*논란)",
            "논란 소지가 큰 국기·영토 표현이 감지되었습니다.",
        ),
    ]
    for cat, pat, msg in raw:
        _SENSITIVE_PATTERNS.append((cat, re.compile(pat, re.IGNORECASE), msg))


@dataclass(frozen=True)
class FilterIssue:
    category: str
    message: str
    matched: str
    field: str


class ContentFilterError(Exception):
    """기획·문안이 안전 규칙을 통과하지 못함."""

    def __init__(self, issues: list[FilterIssue]) -> None:
        self.issues = issues
        super().__init__(format_filter_message(issues))


def format_issues_for_revision(issues: list[FilterIssue]) -> str:
    """LLM 기획 수정 재요청용 요약."""
    if not issues:
        return ""
    lines = ["[필터 위반 — 다음을 중립·정책 홍보 표현으로 바꿔 JSON만 다시 출력]"]
    for iss in issues[:15]:
        lines.append(f"- [{iss.field}] {iss.message} (문제어: «{iss.matched[:50]}»)")
    if len(issues) > 15:
        lines.append(f"- … 외 {len(issues) - 15}건")
    return "\n".join(lines)


def format_filter_message(issues: list[FilterIssue]) -> str:
    if not issues:
        return ""
    lines = ["정서·이미지 안전 필터에 의해 차단되었습니다. 아래 항목을 수정한 뒤 다시 시도하세요."]
    for i, iss in enumerate(issues[:12], 1):
        lines.append(f"{i}. [{iss.field}] {iss.message} (매칭: «{iss.matched[:40]}»)")
    if len(issues) > 12:
        lines.append(f"… 외 {len(issues) - 12}건")
    return "\n".join(lines)


def _scan_fragment(text: str, field: str) -> list[FilterIssue]:
    _compile_patterns()
    if not text or not str(text).strip():
        return []
    issues: list[FilterIssue] = []
    for cat, pat, msg in _SENSITIVE_PATTERNS:
        m = pat.search(text)
        if m:
            issues.append(
                FilterIssue(
                    category=cat,
                    message=msg,
                    matched=m.group(0),
                    field=field,
                )
            )
    return issues


def scan_text(text: str, *, field: str = "본문") -> list[FilterIssue]:
    return _scan_fragment(text, field)


def scan_plan_dict(plan_dict: dict[str, Any] | None) -> list[FilterIssue]:
    """기획 JSON 전체를 키워드·규칙 기반으로 검사."""
    if not plan_dict:
        return []
    issues: list[FilterIssue] = []
    issues.extend(_scan_fragment(str(plan_dict.get("series_title", "")), "시리즈명"))
    issues.extend(_scan_fragment(str(plan_dict.get("head_copy", "")), "헤드카피"))
    for i, slide in enumerate(plan_dict.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        prefix = f"페이지 {i + 1}"
        issues.extend(_scan_fragment(str(slide.get("title", "")), f"{prefix} 제목"))
        for j, b in enumerate(slide.get("bullets") or []):
            issues.extend(_scan_fragment(str(b), f"{prefix} 불릿 {j + 1}"))
        fn = slide.get("footnote")
        if fn:
            issues.extend(_scan_fragment(str(fn), f"{prefix} 각주"))
    return issues


def run_plan_generation_filter(plan_dict: dict[str, Any] | None) -> list[FilterIssue]:
    """기획안 생성 직후 검사. 위반 목록을 반환(없으면 통과)."""
    return scan_plan_dict(plan_dict)


def assert_plan_safe(plan_dict: dict[str, Any] | None) -> None:
    issues = run_plan_generation_filter(plan_dict)
    if issues:
        raise ContentFilterError(issues)


def assert_press_text_safe(text: str) -> None:
    """추출 보도자료에 민감 키워드가 많을 때 기획 전 경고용."""
    issues = scan_text(text[:120_000], field="보도자료")
    if issues:
        raise ContentFilterError(issues)


def append_image_safety(prompt: str) -> str:
    return prompt.rstrip() + "\n" + IMAGE_VISUAL_SAFETY_BLOCK
