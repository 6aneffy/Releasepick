"""Generate Instagram caption draft via OpenAI."""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from content_filter import ContentFilterError, scan_text

MAX_CAPTION_LEN = 2200

DEFAULT_CAPTION_SYSTEM_PROMPT = """\
당신은 재정경제부 공식 Instagram 카드뉴스 게시물의 캡션을 작성하는 카피라이터입니다.

[작성 목표]
- 카드뉴스 이미지(들)와 함께 게시할 한국어 캡션 1개를 작성한다.
- 정치·이념·차별·혐오 표현 금지. 특정 정당·인물 명시 금지.
- 1인칭/2인칭("여러분", "당신") 직접 호명 금지.
- 주체는 "대한민국 경제", "정부", "재정경제부" 등 3인칭.

[구조 — 4블록, 빈 줄로 분리. 2·3블록은 선택]

1. 도입 (1~3행, 필수)
   - 카드 헤드라인/부제를 자연스럽게 인용·변형.
   - 출범 1주년 시리즈면 "국민주권정부 출범 1주년," 프리픽스 사용.
   - 종결 위치에 카드 주제에 어울리는 이모지 1개 선택 (예: 경제 성과 → 📈, 환영·축하 → 👏, 환경 → 🌿, 도약 → 🚀 등 — 주제와 명확히 맞는 것).

2. bullet 블록 (선택)
   - 카드가 박스/항목으로 분할된 경우에만.
   - bullet 선두 이모지는 `✔` 고정.
   - 각 bullet = 카드 박스 제목을 한 줄로 압축. 카드 부제까지 합성 가능. 수치 재기재 금지.
   - bullet 개수 = 카드 박스 개수. 시리즈 인트로면 시리즈 전체 성과 5~6개.

3. 마무리 단락 (선택, 1~3행)
   - 미래지향·정책 의지 또는 슬로건.
   - 종결 이모지 선택 (🚀 👀 🌎✨ 등).
   - 정부 의지 표명에만 "추진해 나가겠습니다" 같은 1인칭 복수 허용.

4. 해시태그 (필수)
   - 출범 1주년 시리즈: 다음 5개를 순서 고정·항상 포함.
     #정부출범1주년 #국민이_만든_대전환의_길 #회복과도약 #모두의1년 #재정경제부
     필요 시 다음 줄에 카드 키워드 해시태그 5~7개 추가.
   - 비-1주년 캠페인: 위 5개 세트 미사용. 캠페인 키워드 7~8개만 (#재정경제부 통상 포함).
   - 띄어쓰기 필요한 태그는 언더스코어 (예: #국민이_만든_대전환의_길). 일반 키워드는 붙임.

[이모지 정책]
- 위치는 도입부 종결 / bullet 선두 / 마무리 단락 종결로 한정.
- 본문 문장 사이 분산 금지.
- 캡션 1개당 총 5~8개 권장.

[수치·표현 규칙]
- 카드의 정확한 수치(예: "8위→5위", "415.4조원", "1.2%p")는 캡션에 재기재 금지.
  단 카드가 단일 수치 메시지의 히어로형(박스 없음)이면 핵심 수치 1개를 산문으로 풀어 쓸 수 있음.
- 마침표·느낌표·물음표 외 종결 부호 금지.
- 영문 단어 남발 금지 (카드 안 영문 명칭 인용은 허용).
- 캡션 본문 1700자 초과 금지 (해시태그 제외 권장 상한, 절대 한도 2200자).

[입력]
- 보도자료 본문(텍스트)과 확정 기획안 JSON(slides, head_copy, series_title)이 user 메시지로 전달됨.
- 이미지의 박스 개수·헤드라인 유형은 기획 JSON의 slides에서 추론.

[출력]
- 캡션 하나만 출력. 설명, 해설, 메타텍스트, 마크다운 코드블럭 절대 금지.
"""


def _trim(text: str, limit: int = MAX_CAPTION_LEN) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def generate_instagram_caption(
    client: OpenAI,
    press_text: str,
    plan_dict: dict[str, Any] | None,
    *,
    system_prompt: str | None = None,
    model: str = "gpt-4o-mini",
    max_tokens: int = 800,
) -> str:
    sys_prompt = system_prompt or DEFAULT_CAPTION_SYSTEM_PROMPT
    plan_summary = json.dumps(plan_dict or {}, ensure_ascii=False)
    press_excerpt = (press_text or "").strip()[:6000]

    user_msg = (
        "다음은 카드뉴스의 기반이 된 보도자료 본문과 확정된 기획 JSON입니다.\n"
        "이를 근거로 Instagram 게시물 캡션을 한국어로 작성하세요.\n"
        f"- 최대 {MAX_CAPTION_LEN}자.\n"
        "- 카드 이미지에 이미 들어간 문구를 그대로 반복하지 마세요.\n"
        "- 정치·이념·혐오·차별적 표현 금지.\n\n"
        "[보도자료 본문]\n"
        f"{press_excerpt}\n\n"
        "[기획 JSON]\n"
        f"{plan_summary}"
    )

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=max_tokens,
    )
    caption = (resp.choices[0].message.content or "").strip()
    caption = _trim(caption)

    issues = scan_text(caption, field="caption")
    if issues:
        raise ContentFilterError(issues)
    return caption
