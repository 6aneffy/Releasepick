# 릴리즈픽 (ReleasePick)

> **생성형 AI 기반 정책 보도자료 → 카드뉴스 인포그래픽 자동 생성 웹서비스**
> 재정경제부 혁신정책담당관·규제개혁법무담당관 (이주호 · 박진영 · 신채은)

보도자료 PDF/HWPX 한 건을 업로드하면, **AI가 핵심 문구를 추출 → 기획안을 작성 → 정부 디자인 가이드 준수 카드뉴스(한국어·영어) JPEG**를 자동 생성하고 **Instagram에 바로 발행**까지 이어지는 Streamlit 기반 MVP 입니다.

평균 **2일 이상**, **건당 약 300만 원** 들던 외주 제작 흐름을 **15~20분, 비용 0원**으로 단축하는 것이 목표입니다.

---

## 1. 기획서 ↔ 구현 매핑

| 기획서 워크플로우 | 구현 모듈 / 단계 | 상태 |
|---|---|---|
| ① 공식 홈페이지 보도자료 PDF 자동 크롤링 | [`code/press_release.py`](code/press_release.py) — mofe.go.kr RSS + 상세 페이지에서 PDF·HWPX·HWP 첨부 메타 자동 수집 (Step 1) | ✅ |
| ② AI 분석 및 기획 (핵심 문구 추출 + 디자인 기획) | [`code/plan_llm.py`](code/plan_llm.py) — OpenAI `gpt-*` 호출 → [`code/models.py`](code/models.py)의 `CardNewsPlan` (Pydantic) JSON 산출. [`code/pdf_extract.py`](code/pdf_extract.py) · [`code/hwpx_extract.py`](code/hwpx_extract.py) 로 본문 추출 (Step 2) | ✅ |
| ③ 스타일 적용 (규격화 템플릿 매칭) | [`themes/`](themes/) (`mofe_body.yaml`, `template1`, `template2/템플릿1·2`) + [`code/template_catalog.py`](code/template_catalog.py) · [`code/template_resources.py`](code/template_resources.py) · [`code/image_gen.py`](code/image_gen.py) · [`code/render_cards.py`](code/render_cards.py) (Step 3·4) | ✅ |
| ④ 담당자 직접 텍스트 · 디자인 미세 조정 | Step 2에서 페이지별 제목·불릿·각주 인라인 편집(1차 승인 후 최대 2회 수정). Step 4에서 표지/완성 시안 **A·B·C 3종 생성 → 선택** (`generate_cover_variant_jpegs`) | ✅ |
| ⑤ 최종 승인 (내부 회람) | `plan_phase` 상태 머신: `draft → post_first → locked` ([`code/state.py`](code/state.py)). 확정 전에는 카드 생성 비활성화 | ✅ |
| ⑥ 다운로드 및 SNS 실시간 자동 배포 | Step 5 ZIP 패키지 ([`code/package_export.py`](code/package_export.py) — PPTX 기획안 + `jpeg/ko/`, `jpeg/en/`) + Step 6 Instagram 자동 발행 ([`code/supabase_storage.py`](code/supabase_storage.py) → [`code/buffer_publish.py`](code/buffer_publish.py)) | ✅ |
| 다국어 (영문) 외신 홍보 | [`plan_llm.translate_plan_to_english`](code/plan_llm.py) + GPT Image 영문 세트 (로고 워드마크 `Ministry of Finance and Economy`) | ✅ |
| 맞춤형 디자인 툴 (템플릿·MI·폰트) | 800×1000 캔버스, 맑은 고딕 / 맑은 고딕 Bold, `themes/mofe_body.yaml` 섹션 톤 5종(neutral·green·blue·purple·orange), 본문 레이아웃 2종(여백형·흰 카드형), 캐릭터 PNG 업로드 | ✅ |
| 정서·이미지 안전 검토 (기획서 비포함, 자체 강화) | [`code/content_filter.py`](code/content_filter.py) — 일본·식민지 잔재, 북한, 정치 이념(보수·진보), 젠더·세대·지역 갈등, 혐오 표현을 LLM 기획·이미지 프롬프트·생성 전에 차단 | ✅ (자체 추가) |
| 세션 복구 | [`code/job_store.py`](code/job_store.py) — `data/jobs.sqlite` 에 단계별 스냅샷 저장, 새로고침/세션 복귀 시 복원 | ✅ (자체 추가) |

---

## 2. 사용자 플로우 (Streamlit 6단계)

[`code/app.py`](code/app.py) 는 얇은 라우터이고 실제 화면은 [`code/views/`](code/views/) 에 있습니다.

```
[Step 1] 보도자료 선택
  └─ "최신 보도자료 불러오기" → mofe.go.kr RSS 5건 표시
     → 행에서 PDF / HWPX 첨부 1건 선택 → 본문 자동 추출
     → 총 페이지 수(1~12) 슬라이더, 멀티페이지 템플릿 변형(v1·v2) 선택

[Step 2] 내용 분석 · 기획안
  └─ "AI 분석 시작" → OpenAI 호출 → CardNewsPlan(JSON) 생성
     → 안전 필터 자동 검사 → 페이지별 제목·불릿·각주 인라인 편집
     → "1차 승인" 후 최대 2회 수정 → "기획 확정 →" (잠금)

[Step 3] 디자인 설정
  └─ 템플릿 YAML, 섹션 컬러 톤(5색 스와치), 로고 위치(상우/상좌/하중),
     캐릭터 PNG, 제목/본문 색상, 본문 레이아웃(여백형 A · 흰 카드형 B),
     폰트 크기 배율(0.75~1.25), 이미지 생성 모델(GPT Image 계열) 선택
     ※ 디자인 컨셉은 페이지 수에 맞춰 자동 추천

[Step 4] 카드 이미지 생성 (JPEG)
  └─ ① "표지 시안 3종 (A/B/C)" 생성 (1장이면 결과물 후보 3종)
     ② 시안 선택
     ③ "한국어 카드 생성" → 800×1000 JPEG (page 1~N)
     ※ 안전 필터 통과한 기획만 API 호출

[Step 5] 결과 확인 · 산출물
  └─ 썸네일 레일 + 미리보기 + 페이지별 재렌더 (최대 2회)
     → "영문 세트 번역·생성" → `jpeg/en/` 추가 생성
     → "ZIP 다운로드" — `기획안_최종.pptx` + `jpeg/ko/`, `jpeg/en/`

[Step 6] SNS 업로드 (선택)
  └─ "캡션 초안 생성" → OpenAI 가 한국어 캡션 초안
     → Supabase Storage 에 카드 임시 호스팅
     → Buffer GraphQL API 로 Instagram 캐러셀 발행 (최대 10장)
     → 발행 후 Supabase 임시 파일 정리
```

각 단계 진입 가능 여부는 [`code/views/editor.py`](code/views/editor.py) 의 `_next_disabled(step)` 가 게이트합니다.

---

## 3. 폴더 구조

```
Releasepick/
├─ README.md                        ← 본 문서
├─ .env-sample                      ← 환경변수 템플릿
├─ requirements.txt                 ← 의존성 (streamlit / openai / pymupdf / pillow / pydantic / pptx / requests / bs4)
├─ design.md                        ← 디자인 가이드 (담당자·디자이너용 톤앤매너)
├─ MERGE_GUIDE_SNS_UPLOAD.md        ← Section 6(SNS 업로드) 머지 가이드
├─ logo.png                         ← 한국어 기본 로고 (직접 렌더 + AI 참조)
├─ 01.jpg / 02.jpg / 03.jpg         ← 기획서 첨부 샘플
│
├─ code/
│  ├─ app.py                        ← Streamlit 멀티페이지 라우터 (얇은 shell)
│  ├─ views/
│  │   ├─ landing.py                ← 홈 (히어로 + bento 피처 그리드)
│  │   ├─ editor.py                 ← Step 1~4, 6 + 단계 푸터
│  │   └─ result_view.py            ← Step 5 결과 확인 + 영문 번역 + ZIP
│  ├─ ui/
│  │   ├─ theme.py                  ← 전역 CSS / 디자인 토큰
│  │   ├─ components.py             ← top_app_bar, step_nav, pill, feature_card …
│  │   └─ assets.py                 ← logo / hero mock data URI
│  │
│  ├─ press_release.py              ← mofe.go.kr RSS + 첨부 메타 크롤러 (재시도·세션)
│  ├─ pdf_extract.py                ← PyMuPDF 기반 PDF 본문 추출
│  ├─ hwpx_extract.py               ← HWPX (OWPML) 본문 추출 (표준 라이브러리만)
│  │
│  ├─ plan_llm.py                   ← OpenAI 기반 CardNewsPlan 생성 + EN 번역
│  ├─ caption_llm.py                ← Instagram 한국어 캡션 초안 생성
│  ├─ content_filter.py             ← 정서·이미지 안전 필터 (기획·프롬프트·산출 3중)
│  ├─ models.py                     ← Pydantic CardNewsPlan / SlidePlan
│  │
│  ├─ template_catalog.py           ← 1페이지·멀티페이지 디자인 컨셉 카탈로그·추천
│  ├─ template_resources.py         ← 멀티페이지 표지/본문 템플릿 변형 로드
│  ├─ template_thumbnails.py        ← 컨셉 썸네일 생성
│  ├─ image_gen.py                  ← GPT Image (OpenAI Images API) 카드 생성
│  │                                   - 표지 시안 3종 (variant A/B/C)
│  │                                   - 한국어 → 영문 세트 (로고 워드마크 자동 교체)
│  ├─ render_cards.py               ← Pillow 기반 직접 렌더 (테마 YAML, 섹션 톤, 로고 박스)
│  ├─ english_logo.py               ← 영문 카드용 로고 비트맵 합성
│  │
│  ├─ export_plan_pptx.py           ← python-pptx 로 기획안 PPTX 빌드 (검수용)
│  ├─ package_export.py             ← PPTX + JPEG → ZIP 패키징
│  │
│  ├─ supabase_storage.py           ← Supabase Storage 업로드/삭제 (서비스 롤 키)
│  ├─ buffer_publish.py             ← Buffer GraphQL `createPost` 로 Instagram 발행
│  │
│  ├─ state.py                      ← session_state defaults / hydrate / persist / guard
│  └─ job_store.py                  ← SQLite (`data/jobs.sqlite`) 스냅샷 저장·복구
│
├─ themes/                          ← 디자인 정본
│  ├─ mofe_body.yaml                ← 본문 색·타이포·섹션 톤·로고 박스
│  ├─ template1/                    ← 1페이지 포스터형 (`템플릿-1.txt`)
│  └─ template2/                    ← 멀티페이지 (2~5+ 페이지)
│      ├─ # Multi-Page Card News (2~5 Pages).txt
│      ├─ 템플릿1/                  ← v1 「재정경제부 1」 표지·본문
│      └─ 템플릿2/                  ← v2 「재정경제부2 (모모페페 캐릭터)」 표지·본문
│
└─ data/
   ├─ jobs.sqlite                   ← 세션 스냅샷
   └─ logo_en_mofe.png              ← 영문 로고 워드마크
```

---

## 4. 환경 설정

### 4.1 필수 — OpenAI

저장소 루트 `Releasepick/.env` 에 다음 키를 설정합니다 (없으면 Step 2 부터 오류).

```env
OPENAI_API_KEY=sk-...
```

### 4.2 선택 — Step 6 Instagram 자동 발행

아래 5개 키가 **모두** 채워져야 Step 6 가 활성화됩니다. 하나라도 비면 화면 자체가 비활성화되어 기존 1~5단계는 그대로 동작합니다 ([`editor.py:96-104`](code/views/editor.py#L96-L104)).

```env
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_BUCKET=
BUFFER_API_KEY=
BUFFER_CHANNEL_ID=              # Buffer 채널 설정 URL 의 hex 24자리
BUFFER_ORGANIZATION_ID=         # 선택
```

캡션 톤은 [`code/caption_llm.py`](code/caption_llm.py) 의 `DEFAULT_CAPTION_SYSTEM_PROMPT` 를 편집해 조정합니다. 머지/회귀 관련 주의사항은 [`MERGE_GUIDE_SNS_UPLOAD.md`](MERGE_GUIDE_SNS_UPLOAD.md) 참조.

### 4.3 디자인 커스터마이즈

- 카드 해상도: **800 × 1000 px** (Instagram 4:5 세로형)
- 한글 폰트: Windows `malgun.ttf` / `malgunbd.ttf` 자동 탐색 ([`render_cards.py:16-17`](code/render_cards.py#L16-L17))
- 본문 정본: [`themes/mofe_body.yaml`](themes/mofe_body.yaml)
- 1페이지 가이드: [`themes/template1/템플릿-1.txt`](themes/template1/템플릿-1.txt)
- 멀티페이지 가이드: [`themes/template2/# Multi-Page Card News (2~5 Pages).txt`](themes/template2/)
- 톤앤매너 레퍼런스: [`design.md`](design.md)

---

## 5. 실행

```powershell
# 의존성 설치
cd c:\Users\sangh\Releasepick
uv pip install -r requirements.txt

# 앱 실행
cd code
uv run python -m streamlit run app.py
```

> Windows 에서 `uv run streamlit ...` 직접 호출은 trampoline 오류가 발생할 수 있어 `python -m streamlit` 형태를 권장합니다.

브라우저에서 `http://localhost:8501` → 「홈」 카드의 **"보도자료 업로드하고 시작하기"** 버튼으로 진입.

---

## 6. 데이터 흐름과 아키텍처 포인트

### 6.1 보도자료 수집 (Step 1)

[`press_release.py`](code/press_release.py) 는 mofe.go.kr 의 공식 RSS (`detailRssTagService.do?bbsId=MOSFBBS_000000000028`) 에서 최근 N건의 제목·nttId·발행일·작성자를 수집한 뒤, 각 상세 페이지에서 첨부 목록을 BeautifulSoup 으로 파싱합니다.

- **첨부 우선순위**: PDF > HWPX > HWP. HWP 만 있는 게시물은 UI 에서 "불가" 칩으로 비활성화.
- **WAF 우회**: 정상 브라우저 헤더 풀세트(`Accept`, `Accept-Language`, `Sec-Fetch-*` 등) + Session keep-alive + `ConnectionReset/Timeout` 시 3회 백오프 재시도 (1.5 / 3.0 / 6.0초).
- **캐싱**: `st.cache_data` 로 RSS / 상세 페이지 응답을 캐시하고, 「새로고침」 버튼이 모든 cache 를 `.clear()` 합니다.

### 6.2 본문 추출

- **PDF**: [`pdf_extract.py`](code/pdf_extract.py) 가 PyMuPDF 로 텍스트 레이어 추출. **스캔 전용 PDF 는 본문이 비어 있을 수 있어** 사용자에게 명시적으로 안내합니다.
- **HWPX**: [`hwpx_extract.py`](code/hwpx_extract.py) 가 ZIP 내부 `Contents/section*.xml` 에서 `hp:t` 요소만 순회 — 외부 hwp 의존성 0개.

### 6.3 LLM 기획 (Step 2)

[`plan_llm.py`](code/plan_llm.py) 는 OpenAI Chat Completions 에 다음 3 요소를 합성한 system prompt 를 전달합니다.

1. JSON Schema 강제 블록 (`series_title`, `head_copy`, `slides[role/title/bullets/footnote]`)
2. **선택된 페이지 수**에 따른 슬라이드 역할 규칙 (1장이면 cover 단독, 2장이면 cover + closing, 3장 이상이면 cover + body × N + closing)
3. **현재 선택된 템플릿 변형**의 표지·본문 원문 (`load_cover_template_text`, `load_body_template_text`) — LLM 이 톤·레이아웃 규칙까지 따르도록 합니다
4. [`content_filter.PLAN_EDITOR_SAFETY_RULES`](code/content_filter.py) — 안전 규칙

응답은 Pydantic `CardNewsPlan` 으로 검증 → `st.session_state.plan_dict` 에 저장 → SQLite 스냅샷 저장 (`persist()`).

`plan_phase` 상태 머신:
- `draft` — 자유 편집 + "페이지 편집 반영"
- 「1차 승인」 → `post_first` — 추가 수정 2회 카운트
- 「기획 확정 →」 → `locked` — Step 4 로 진행 가능

### 6.4 안전 필터 (3중)

[`content_filter.py`](code/content_filter.py) 가 차단하는 카테고리:
- 일본 문화/관광/식민지 잔재 (기모노·도리이·후지산·일제강점기·신사 등)
- 북한·분단·주체사상
- 정치 이념 (보수·진보·좌우), 젠더·세대·지역 갈등
- 혐오·차별·선동 표현

적용 지점:
1. **LLM 기획 생성 시** system prompt 에 `PLAN_EDITOR_SAFETY_RULES` 주입
2. **기획안 저장/편집 직후** `assert_plan_safe()` → 위반 시 사용자에게 표시 후 중단 (`ContentFilterError`)
3. **이미지 프롬프트** 마지막에 `IMAGE_VISUAL_SAFETY_BLOCK` (영문 negative prompt) 강제 추가 ([`image_gen.append_image_safety`](code/image_gen.py))

### 6.5 이미지 생성 (Step 4)

[`image_gen.py`](code/image_gen.py) — OpenAI Images API (`gpt-image-*` 계열) 호출. 두 단계:

1. **표지 시안 3종 (variant A/B/C)** — `generate_cover_variant_jpegs`
   - 동일 기획 1페이지를 레이아웃·정렬·3D 소스만 달리 생성
   - 1장 카드뉴스 모드에서는 이것이 곧 **최종 후보**(추가 API 호출 없음)
2. **선택된 시안 스타일을 본문 N장에 일관 적용** — `generate_plan_card_jpegs`
   - 페이지당 1~2분 / 1회 호출
   - 영문 세트는 Step 5 에서 추가로 N회 호출 (요금 2배)

로고는 두 가지 경로:
- **GPT Image 가 카드 안에 직접 그림** — 한국어는 「재정경제부」 워드마크 + 삼태극, 영문은 「Ministry of Finance and Economy」 워드마크. 위치는 `top_right` / `top_left` / `bottom_center` 중 선택.
- **Pillow 직접 렌더 경로** ([`render_cards.py`](code/render_cards.py)) — `logo.png` / `data/logo_en_mofe.png` 합성. 현재 메인 흐름은 GPT Image 경로지만 직접 렌더는 폴백·검수용으로 유지.

### 6.6 결과 산출 (Step 5)

[`package_export.py`](code/package_export.py) → ZIP 구조:

```
└─ release-pick-export.zip
   ├─ 기획안_최종.pptx        ← export_plan_pptx.build_plan_pptx_bytes
   └─ jpeg/
       ├─ ko/01_cover.jpg, 02_body.jpg, …
       └─ en/01_cover.jpg, 02_body.jpg, …
```

PPTX 는 텍스트 검수용이며 카드 픽셀과 1:1 대응하지 않습니다 (개정 텍스트 확인용).

### 6.7 SNS 자동 발행 (Step 6, 선택)

```
Supabase Storage (private bucket)            Buffer GraphQL
       ▲                                          ▲
       │ ① upload_card_images()                   │ ② createPost(input)
       │   service-role key + signed URL          │   channelId + media[] + caption
       └────────── 한국어 카드 JPEG ──────────────┘
                       │
                       ▼
                Instagram (Buffer 채널 연결)
```

[`supabase_storage.py`](code/supabase_storage.py) 는 service-role 키로 Storage 에 카드를 업로드하고 외부 접근용 URL 을 반환. [`buffer_publish.py`](code/buffer_publish.py) 는 GraphQL `mutation CreatePost` 를 호출해 Instagram 캐러셀(최대 10장)을 즉시 발행합니다. 발행 직후 "Supabase 임시 파일 정리" 버튼으로 호스팅 잔여물을 삭제합니다.

### 6.8 세션 복구

[`state.persist()`](code/state.py) 는 모든 단계에서 `st.session_state` 의 직렬화 가능한 키를 모아 [`job_store.save_snapshot`](code/job_store.py) 로 `data/jobs.sqlite` 에 저장합니다. 새로고침/세션 복귀 시 `try_hydrate()` 가 같은 `session_id` 의 스냅샷을 복원하므로, 이미지 생성 도중 새로고침해도 직전 상태부터 이어 작업 가능합니다.

---

## 7. 도입 효과 (기획서 대비 검증)

| 항목 | Before (기획서) | After (구현) |
|---|---|---|
| 카드뉴스 제작 비율 | 보도자료 143건 중 10건 (7%) | 보도자료 1건당 약 15~20분 → 사실상 모든 보도자료 처리 가능 |
| 1건 제작 소요 시간 | 외주·내부 모두 최소 2~3일 | 본문 추출 ~1분 + 기획 ~30초 + 카드 N장 × 1~2분 + 영문 세트 N분 ≈ **15~20분** |
| 1건 제작 비용 | 외주 약 3백만 원 | OpenAI API 종량 과금 (보통 수십~수백원 / 건) ≈ **사실상 0원** |
| 일관된 브랜딩 | 외주마다 편차 | 전용 템플릿(v1/v2) + 톤 5색 + 로고 위치 표준화 |
| 다국어 (영문) | 별도 외주 | 동일 흐름에서 자동 번역 + AI 로고 워드마크 교체 |
| 회람·검토 | 이메일 왕복 | 화면 내 1차 승인 + 최대 2회 수정 상태 머신 |
| SNS 적시성 | 수작업 업로드 | Buffer API 로 Instagram 캐러셀 즉시 발행 |

---

## 8. 제한 사항 / 주의

- **텍스트 추출 가능한 PDF** 권장. 스캔 전용 PDF·이미지 PDF 는 본문이 비어 추출 실패합니다.
- **HWP (구버전)** 는 첨부 목록에서 감지되지만 추출은 **불가**. HWPX 또는 PDF 첨부가 있는 게시물만 선택 가능.
- 카드뉴스 페이지 수는 **1~12** 지원. Instagram 캐러셀 한도(10장)를 넘으면 Step 6 가 차단합니다.
- GPT Image 호출은 **페이지당** 발생하며, 영문 세트 생성 시 **거의 2배**의 API 비용이 발생합니다.
- 안전 필터를 통과하지 않은 기획은 **API 호출 없이 중단** — 위반 항목과 가이드가 화면에 표시됩니다.
- 세션 상태는 메모리 + SQLite 스냅샷. 다른 PC 에서 같은 세션 이어받기는 지원하지 않습니다.

---

## 9. 참고 문서

- [`design.md`](design.md) — 카드뉴스 디자인 톤앤매너 (담당자/디자이너용)
- [`MERGE_GUIDE_SNS_UPLOAD.md`](MERGE_GUIDE_SNS_UPLOAD.md) — Section 6 (Instagram 업로드) 머지·회귀 방지 가이드
- [`themes/template1/템플릿-1.txt`](themes/template1/) — 1페이지 포스터형 정본
- [`themes/template2/# Multi-Page Card News (2~5 Pages).txt`](themes/template2/) — 멀티페이지 정본
