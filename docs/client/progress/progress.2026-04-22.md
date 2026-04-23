# Client Progress - 2026-04-22

## 완료된 작업

### #316 게시글 상세 SSR slug double encoding으로 인한 404 수정 (PR #317 머지)

운영 환경에서 발행된 게시글 상세 페이지가 public 목록과 backend API에서는 정상 조회되는데도 `NEXT_NOT_FOUND`로 렌더되던 문제를 수정했다. 진단 로그로 확인한 결과, public 상세 SSR 경로에서 이미 percent-encoded 상태로 들어온 slug를 `fetchPostBySlug()`가 다시 `encodeURIComponent()` 하면서 `%EC...`가 `%25EC...`로 변형되고 있었고, 이로 인해 backend route miss 404가 발생했다. 수정은 `main` 브랜치 이슈 `#316` 기준으로 진행했고, `fetchPostBySlug()`가 먼저 원래 slug로 canonical path를 만들고, 404일 때만 decode fallback을 한 번 더 시도하도록 바꿨다. 이렇게 해서 실제로 인코딩된 경로 입력은 복구하면서도 문자 그대로의 `%xx` 시퀀스를 slug로 사용하는 경우의 회귀를 피했다. PR `#317`은 동기 `codex` 리뷰 2라운드 후 clean 판정으로 병합됐다.

**주요 변경 사항:**

- `src/entities/post/api.ts`
  - `fetchPostBySlug()`에 slug path builder를 분리
  - 1차 요청은 원래 slug를 `normalize("NFKC")` 후 canonical path로 조회
  - 1차 요청이 404일 때만 `decodeURIComponent()` fallback을 시도하고, decode 결과가 원본과 다를 때에만 재조회
  - `ApiResponseError(404)`가 아닌 에러는 그대로 전파

**검증:**

- `pnpm install --frozen-lockfile`
- `pnpm compile:types`
- `pnpm lint` *(저장소 기존 warning 2건 유지)*
- `pnpm build`

**메모:**

- `pnpm lint`는 저장소 기존 warning인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용 1건과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.
- 운영에서 사용한 임시 진단 로그는 별도 `release` 확인용 커밋으로만 다뤘고, 이번 `main` 머지에는 포함하지 않았다.
- category/tag slug가 운영 DB에서 빈 문자열인 문제는 별도 후속 작업이 필요하다.
