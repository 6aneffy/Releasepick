# 릴리즈픽 — 카드뉴스 제작 (Streamlit MVP)

보도자료 PDF 업로드 → LLM 기획안 → 1차 승인·기획 수정(최대 2회) → **한국어·영어** JPEG 카드(동일 템플릿) → 산출물 검토·재렌더(최대 2회) → 최종 ZIP(PPTX 기획안 + `jpeg/ko/`, `jpeg/en/`).

페이지 수는 **1장 이상** 설정 가능합니다.

## 준비

1. 저장소 루트 [`AI-Education/.env`](../.env)에 `OPENAI_API_KEY` 설정.
2. (선택) `design.md`와 `themes/`를 기관 가이드에 맞게 조정.

## 실행

```powershell
cd c:\Users\maria\AI-Education
uv pip install -r 9.CardNews/requirements.txt
uv run streamlit run 9.CardNews/code/app.py
```

## 제한

- **텍스트 추출 가능한 PDF**를 권장합니다. 스캔 전용 PDF는 본문이 비어 있을 수 있습니다.
- 세션 상태는 기본적으로 메모리에만 있으며, **SQLite**(`jobs.sqlite`)에 스냅샷을 저장해 새로고침 시 복구를 시도합니다.

## 폴더 구조

- `code/` — 앱 및 모듈
- `themes/` — YAML 테마 (cover / body / closing variant)
- `design.md` — 디자인 레퍼런스(사람용)
- 디자인 정본: 상위 폴더 `국장님믿고갑조/템플릿(본문).txt` — 카드 해상도 **800×1000**, 기본 로고는 저장소 루트 `logo.png`(있으면 자동 사용).
- **AI 일러스트**: **GPT Image** 모델 선택 후 카드 생성 시, 슬라이드당 **한국어·영어 각 1회** Images API 호출(페이지 수의 약 2배, 요금 발생). 동일 표지·본문 템플릿과 디자인 설정을 사용합니다.
- **정서·이미지 안전**: `code/content_filter.py` — 일본·북한·식민지 잔재, **정치 이념(보수·진보 등)·젠더·세대·지역 갈등·혐오 표현**을 기획·프롬프트·생성 전에 차단합니다.
