# MERGE_GUIDE — Instagram 자동 업로드 (Buffer + Supabase)

이 PR은 Releasepick에 **Section 7: 인스타그램 자동 업로드** 기능을 추가합니다. 본 문서는 PR을 **현재보다 더 발전한 upstream main 브랜치**에 머지할 때 충돌을 줄이고 회귀 위험을 0으로 만들기 위한 가이드입니다.

## 변경 요약

- 신규 모듈 3개: `code/supabase_storage.py`, `code/buffer_publish.py`, `code/caption_llm.py`
- 신규 문서: `MERGE_GUIDE_SNS_UPLOAD.md` (이 문서)
- 수정: `code/app.py` (env 로딩 + session state + Section 7 UI), `requirements.txt` (`requests` 추가), `README.md` (준비 단락)
- env 키 신규 6개 (모두 선택. 미설정 시 Section 7 자동 비활성)

## 핵심 설계 원칙

- **회귀 0**: 모든 새 env 키가 하나라도 비어 있으면 `_SNS_READY = False`. Section 7 자체가 렌더되지 않음. 기존 1~6단계 동작 100% 유지.
- **신규 파일 우선**: 핵심 로직은 모두 신규 모듈에 격리. `app.py` 변경은 최소(imports + env + session state + Section 7 호출 + 두 헬퍼 함수).
- **시멘틱 앵커**: 라인 번호 의존 금지. 함수명·섹션 제목·state key 명명을 기준으로 머지.

## 충돌 위험 평가

| 항목 | 위험 | 처리 |
|---|---|---|
| `code/supabase_storage.py` | 낮음 | 신규 파일. 동일 경로 선점 여부만 확인. |
| `code/buffer_publish.py` | 낮음 | 신규 파일. |
| `code/caption_llm.py` | 낮음 | 신규 파일. upstream에 비슷한 이름 모듈이 있으면 함수만 이전. |
| `code/app.py` | **높음** | 섹션 번호·state key·렌더 흐름이 upstream에서 바뀌었을 가능성. 아래 "통합 절차" 참조. |
| `requirements.txt` | 낮음 | `requests>=2.32.0` 줄 추가만. |
| `.env` | 해당 없음 | gitignore. PR에 포함하지 않음. |
| `README.md` | 중간 | "준비" 단락에 항목 추가. 충돌 시 키 목록만 살리고 본문 통합. |

## 브랜치 / 커밋 전략

```
git fetch origin
git checkout -b feature/instagram-buffer-upload origin/main
# upstream 변화 발생 시
git rebase origin/main
```

커밋 분리 (리뷰 편의):
1. `chore: add requests dep`
2. `feat(sns): supabase_storage module`
3. `feat(sns): buffer_publish module`
4. `feat(sns): caption_llm module + default prompt placeholder`
5. `feat(app): section 7 instagram upload + caption editor`
6. `docs: README sns 준비 단락 + MERGE_GUIDE_SNS_UPLOAD.md 추가`

## app.py 통합 시 시멘틱 앵커 (라인 번호 의존 금지)

upstream `app.py`가 변형된 경우 다음 패턴으로 삽입 지점을 찾아 적용:

1. **Import 블록**
   - 앵커: `from package_export import build_export_zip_bytes` 또는 유사한 기존 import.
   - 추가:
     ```python
     from buffer_publish import BufferError, create_instagram_post
     from caption_llm import (
         DEFAULT_CAPTION_SYSTEM_PROMPT,
         MAX_CAPTION_LEN,
         generate_instagram_caption,
     )
     from supabase_storage import (
         SupabaseStorageError,
         UploadedAsset,
         delete_objects,
         upload_card_images,
     )
     ```
   - 알파벳 정렬 규칙이 있으면 그 위치에 끼워 넣음.

2. **Env 로딩 블록**
   - 앵커: `OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", ...).strip()`
   - **바로 아래에** 추가:
     ```python
     SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
     SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
     SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "").strip()
     BUFFER_API_KEY = os.getenv("BUFFER_API_KEY", "").strip()
     BUFFER_CHANNEL_ID = os.getenv("BUFFER_CHANNEL_ID", "").strip()
     BUFFER_ORGANIZATION_ID = os.getenv("BUFFER_ORGANIZATION_ID", "").strip()
     _SNS_READY = bool(
         SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY and SUPABASE_BUCKET
         and BUFFER_API_KEY and BUFFER_CHANNEL_ID
     )
     ```

3. **Session state 초기화 (`_init_session()` 또는 동등 함수)**
   - 앵커: `defaults = {` 딕셔너리.
   - 추가 키:
     ```python
     "instagram_caption": "",
     "instagram_uploaded_post_id": None,
     "instagram_uploaded_keys": [],
     "instagram_cleanup_done": False,
     ```
   - upstream에 다른 이름의 dict가 있어도 동일 패턴으로 추가.

4. **세션 스냅샷 (`_snapshot()` 함수)**
   - 위 4개 키 모두 dict에 추가하여 새로고침 시 복원되도록 함.

5. **Section 7 호출 위치**
   - 앵커: Section 6의 ZIP 다운로드 블록 **끝**. upstream이 이미 Section 7 이상을 도입했으면 다음 비어있는 번호로 변경하고, **의미상 ZIP 다운로드 직후**에 위치하도록 한다.
   - `main()` 함수 내 마지막 줄 (다른 섹션 외부)에 다음 추가:
     ```python
     if _SNS_READY and st.session_state.card_paths:
         _render_section_instagram_upload(client)
     ```

6. **헬퍼 함수 2개**
   - `_render_section_instagram_upload(client)` — Section 7 UI 전체. 발행 후 "Supabase 임시 파일 정리" **수동** 버튼 포함.
   - `_do_instagram_upload(paths_ko)` — Supabase 업로드 → Buffer 발행 핸들러. **성공 시 자동 cleanup 안 함** (race condition 회피, 아래 "Buffer 비동기 이슈" 참조). 실패 시에만 즉시 cleanup.
   - 둘 다 모듈 레벨에 정의 (main() 외부, `if __name__ == "__main__":` 위).
   - 원본 코드의 `_render_*` 류 헬퍼 명명 규칙을 따른다.
   - 버튼 노출 조건은 **로컬 변수가 아닌 `st.session_state` 직접 조회**로 평가. Streamlit 같은-rerun 안에서 핸들러가 state를 바꿔도 그 사이에 계산된 로컬 변수는 stale이라 cleanup 버튼이 보이지 않을 수 있음.

## upstream 변경 가능성에 따른 적응 포인트

리뷰어/통합자가 점검할 항목:

- **`card_paths` state key 변경**: upstream에서 `ko_card_paths` / `cards_ko` / dict 구조로 바뀌었을 수 있음 → `_render_section_instagram_upload`의 `st.session_state.card_paths` 참조를 그 이름으로 교체.
- **OpenAI 클라이언트 위치 변경**: 모듈 분리됐을 가능성 (`code/llm_client.py` 등). `client = OpenAI(...)` 패턴 검색 후 동일 인스턴스 주입.
- **content_filter 함수명 변경**: 본 PR의 `caption_llm.py`가 `scan_text(text, field=...)` / `ContentFilterError`를 사용. upstream에서 이름이 바뀌었으면 import만 조정.
- **세션 멀티유저화**: Supabase 키 패턴에 user id 추가 — `supabase_storage.upload_card_images`의 키 생성 부분만 수정 (`posts/{user_id}/{session_id}/{ts}/...`).
- **이미지 포맷 변경**: JPEG → PNG/WebP 전환 시 `supabase_storage._guess_content_type`이 mimetypes로 자동 처리하므로 무변경.
- **secrets manager 도입**: `os.getenv` 호출을 그 인터페이스로 교체.

## 환경변수

`.env`는 PR에 포함하지 않습니다. upstream에 `.env.example` / `.env.sample` 이 있으면 거기에 키들을 빈 값으로 추가:

```
# SNS 자동 업로드 (선택, 모두 채워야 활성화)
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_BUCKET=
BUFFER_API_KEY=
BUFFER_CHANNEL_ID=
BUFFER_ORGANIZATION_ID=
```

운영 배포 시:
- Supabase 버킷은 **private 권장**. `supabase_storage.get_url`이 1시간 만료 signed URL을 발급.
- `SUPABASE_SERVICE_ROLE_KEY`는 절대 클라이언트(브라우저)로 노출되면 안 됨. 본 PR은 서버 사이드 `app.py`에서만 사용.
- `BUFFER_CHANNEL_ID`는 Buffer 채널 설정 URL 마지막 path segment (24-hex).

## Feature flag 동작

`_SNS_READY = False` 일 때:
- Section 7 자체가 렌더되지 않음
- 기존 Section 6 ZIP 다운로드까지 흐름 동일
- 어떤 신규 모듈도 import는 되지만 호출되지 않음 (네트워크 호출 없음)

운영 롤백: 운영 서버 `.env`에서 SNS 키 중 1개만 제거하면 즉시 비활성. 코드 롤백 불필요.

## 리뷰어 체크리스트

- [ ] `_SNS_READY=False` (env 미설정) 환경에서 기존 Section 1~6 흐름이 변화 없는지 확인
- [ ] `_SNS_READY=True` 환경에서 Section 7 노출 + 캡션 초안 생성 + textarea 수정 + 업로드 버튼 동작
- [ ] 신규 3개 모듈이 단독 import 가능: `python -c "import sys; sys.path.insert(0,'code'); import supabase_storage, buffer_publish, caption_llm; print('ok')"`
- [ ] `SUPABASE_SERVICE_ROLE_KEY`가 클라이언트로 노출되는 경로가 없음 (`grep -RIn "SERVICE_ROLE"` 결과는 `app.py`와 `supabase_storage.py`만)
- [ ] **발행 성공 시 Supabase 자동 cleanup 호출 안 함** (Buffer 비동기 fetch race 방지). 실패 경로(SupabaseStorageError/BufferError)에서만 즉시 cleanup.
- [ ] 발행 성공 후 "Supabase 임시 파일 정리" 수동 버튼 노출 + 클릭 시 `delete_objects` 호출
- [ ] 캡션이 `content_filter.scan_text`를 통과한 경우만 Buffer로 전송
- [ ] 카드 11장 이상이면 명시 에러 + 업로드 차단
- [ ] 캡션 2200자 초과 입력 시 버튼 disabled
- [ ] Buffer GraphQL `createPost` 호출 시 `mode: shareNow` + `metadata.instagram.{type: post, shouldShareToFeed: true}` 포함 (아래 "Buffer GraphQL 실제 스키마" 참조)

## Buffer GraphQL 실제 스키마 (테스트로 확정)

공식 docs는 `mode: now`라고 적혀 있으나 실제 `ShareMode` enum 값은 다름. 인스트로스펙션 결과:

- `ShareMode` enum 유효값: `addToQueue`, `shareNow`, `shareNext`, `customScheduled` — 즉시 발행 = **`shareNow`**.
- Instagram 채널은 `metadata.instagram.{ type, shouldShareToFeed }` 필수. type 없으면 `UnexpectedError: Instagram posts require a type (post, story, or reel)`.
- `PostType` enum 유효값: `post`, `reel`, `story`, `short`, `whats_new`, `offer`, `event`, `carousel`, `ghost_post`, `thread`. 일반 피드 캐러셀 = `post`.
- `shouldShareToFeed`는 NON_NULL Boolean. 피드 게시물이면 `true`.

검증된 mutation variables:
```json
{
  "input": {
    "channelId": "...",
    "text": "<caption>",
    "mode": "shareNow",
    "schedulingType": "automatic",
    "assets": [ { "image": { "url": "..." } }, ... ],
    "metadata": {
      "instagram": {
        "type": "post",
        "shouldShareToFeed": true
      }
    }
  }
}
```

기타 platform 추가 시 동일 패턴 (`metadata.facebook`, `metadata.linkedin` 등 `PostInputMetaData` 필드 각각 별도 입력 타입). 검증은 introspection으로 확인:
```
.venv/Scripts/python.exe -c "
import sys, os; sys.path.insert(0,'code')
from dotenv import load_dotenv; load_dotenv()
from buffer_publish import _post_graphql
print(_post_graphql('{ __type(name: \"ShareMode\") { enumValues { name } } }', {}))
print(_post_graphql('{ __type(name: \"PostType\") { enumValues { name } } }', {}))
"
```

## Buffer 비동기 fetch 이슈 (중요)

`createPost(mode: shareNow)` mutation은 Buffer 큐에 작업 등록 + post id 반환. 실제 Instagram 업로드는 Buffer 워커가 **비동기로 수초~수분 뒤** 처리하며, 그 시점에 Buffer가 `assets[].image.url`을 fetch함.

따라서:
- mutation 응답 직후 Supabase 객체를 삭제하면 Buffer fetch 실패 → Instagram에 미디어 누락(또는 빈 캐러셀).
- **반드시 수동 cleanup**: 운영자가 Instagram에서 게시물·이미지 정상 노출을 눈으로 확인한 뒤 "Supabase 임시 파일 정리" 버튼 클릭.
- 자동화하려면 (a) `instagram_uploaded_keys`에 저장된 키를 N분 후 백그라운드 잡으로 삭제, 또는 (b) Supabase 버킷 lifecycle 정책으로 `posts/` prefix 24시간 후 자동 삭제.

업로드 실패(SupabaseStorageError/BufferError) 경로에서는 이미 올린 객체를 즉시 cleanup해도 안전 (Buffer가 아직 작업을 받지 않았거나 받았어도 IDLE 상태).

## 검증 명령

```
# 1) syntax + 모듈 import
.venv/Scripts/python.exe -c "import ast; ast.parse(open('code/app.py', encoding='utf-8').read()); print('app.py OK')"
.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'code'); import supabase_storage, buffer_publish, caption_llm; print('SNS modules OK')"

# 2) Buffer 채널 조회 (API 키가 유효한지)
.venv/Scripts/python.exe -c "
import sys, os; sys.path.insert(0,'code')
from dotenv import load_dotenv; load_dotenv()
from buffer_publish import list_instagram_channels
print(list_instagram_channels(os.environ['BUFFER_ORGANIZATION_ID']))
"

# 3) E2E
uv run streamlit run code/app.py
```

## PR 본문 템플릿

```markdown
## Summary
- Section 7 추가: 한국어 카드뉴스 캐러셀을 Buffer GraphQL API로 즉시 발행
- Supabase Storage를 임시 CDN으로 사용 (signed URL 1h)
- OpenAI 기반 캡션 초안 생성 + textarea 수정 가능
- env 키 미설정 시 자동 비활성 — 회귀 위험 0

## New modules
- `code/supabase_storage.py` — 카드 JPEG 업로드/URL/삭제
- `code/buffer_publish.py` — Buffer GraphQL `createPost` (`mode: shareNow`, `metadata.instagram.{type, shouldShareToFeed}`, assets 캐러셀)
- `code/caption_llm.py` — 캡션 생성 + 안전 필터

## Changed
- `code/app.py` — env, session state, Section 7 호출 + 헬퍼
- `requirements.txt` — `requests` 추가
- `README.md` — SNS 준비 단락
- `MERGE_GUIDE_SNS_UPLOAD.md` — 본 머지 가이드

## Env keys (운영 .env에 추가)
- `BUFFER_API_KEY`, `BUFFER_CHANNEL_ID`, `BUFFER_ORGANIZATION_ID`
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_BUCKET`

## Test plan
- [ ] env 키 없이 실행 → Section 7 미노출, 기존 흐름 정상
- [ ] env 설정 후 샘플 PDF로 캐러셀 3장 발행 → Instagram 게시 + 캐러셀 미디어 정상 표시
- [ ] post_id 응답 + "Supabase 임시 파일 정리" 수동 버튼 노출
- [ ] 게시물 확인 후 수동 정리 버튼 클릭 → Supabase Storage 비워짐
- [ ] 캡션 2300자 → 버튼 disabled
- [ ] 카드 11장 → 명시 에러
- [ ] BUFFER_API_KEY 무효값 → GraphQL error 메시지 표시

## Rollback
- 운영 .env에서 SNS 키 1개 제거 → 즉시 회귀
- 코드 롤백 불필요. 부분 revert 가능 (커밋 6분리)

## Notes for reviewers
- Buffer migration 2026-05-25 이후 assets 신규 shape 필수 — 본 PR은 신규 shape만 사용
- 공식 docs는 `mode: now`라 적혀 있으나 실제 enum은 `shareNow`. 본 PR은 introspection으로 확인된 값 사용
- Instagram 채널은 `metadata.instagram.{type, shouldShareToFeed}` 필수 — 누락 시 `UnexpectedError: Instagram posts require a type`
- Buffer는 mutation 응답 후 워커가 **비동기로** 이미지 fetch → Supabase cleanup은 반드시 수동/지연 (자동 cleanup 금지)
- Carousel 최대 10장은 Instagram 정책
```
