# Server Progress — 2026-05-03

## Issue #123 — Post 공개 접근과 검색엔진 색인 정책 분리

- PR: pyo-sh/pyosh-blog-be#125
- 상태: 머지 완료

### 작업 내용

- `post_tb.search_indexable` 컬럼과 Drizzle schema/migration/meta snapshot을 추가했다.
- Posts API request/response schema에 `searchIndexable`을 반영했다.
- 공개 읽기 조건을 `status=published`, `visibility=public`, `deletedAt IS NULL`로 공통화하고, 검색 색인 조건은 여기에 `searchIndexable=true`를 추가하도록 정리했다.
- `/posts/:slug`, 이전/다음 글, 댓글 조회/작성, view-count/인기글 대상에서 private/draft/archived 글을 404 정책으로 차단했다.
- `/posts/slugs`와 `/sitemap.xml`은 search-indexable 글만 포함하고, `/posts`, RSS, stats popular는 noindex 공개 글을 유지하도록 테스트를 보강했다.

### 검증

- `pnpm compile:types`
- `pnpm lint`
- `pnpm test` — 19 files / 311 tests 통과

## Issue #122 - Admin 게시글 삭제 상태 필터 (PR #126 머지)

**Status**: Merged

### What was done

Admin 글 관리의 휴지통 탭이 정상 발행 글까지 함께 보여주던 문제를 수정했다. 기존 `includeDeleted=true`는 삭제 글 전용이 아니라 삭제 글을 포함한 전체 조회 의미로 유지하고, 명시적인 삭제 상태 필터 `deletedState=active|deleted|all`을 `GET /admin/posts`에 추가했다.

서비스 레이어에서는 `deletedState=deleted`일 때 `deleted_at IS NOT NULL`, `deletedState=active`일 때 `deleted_at IS NULL`, `deletedState=all`일 때 삭제 조건 없음으로 처리한다. 하위 호환을 위해 `deletedState`가 생략되고 `includeDeleted=true`인 경우만 `all`로 해석한다. 리뷰 경고에 따라 `deletedState=active&includeDeleted=true`는 명시 상태가 우선하여 active 글만 반환하도록 회귀 테스트를 추가했다.

**파일 변경:**
- `src/routes/posts/post.schema.ts`: Admin 목록 쿼리에 `deletedState` 추가, `includeDeleted` 설명을 하위 호환 의미로 정리.
- `src/routes/posts/post.service.ts`: 명시적 삭제 상태 필터와 legacy `includeDeleted=true` fallback 분리.
- `src/routes/posts/post.route.ts`: Admin 목록 OpenAPI 설명 갱신.
- `test/routes/posts.test.ts`: `deletedState=deleted`, `deletedState=all`, `deletedState=active&includeDeleted=true`, `includeDeleted=false` 회귀 테스트 보강.
- `api-spec.md`: Admin posts 쿼리 문서에 `deletedState`와 legacy `includeDeleted` 의미 추가.

### Review

- Codex review 1차: `0 critical / 1 warning / 0 suggestion`.
- 경고 반영: schema default 제거 후 서비스에서 `query.deletedState ?? (query.includeDeleted ? "all" : "active")`로 fallback 처리.
- Codex review 2차: `0 critical / 0 warning / 0 suggestion` clean.

### Verification

- `pnpm test test/routes/posts.test.ts` -> `92` tests passed
- `pnpm test` -> `19` files, `301` tests passed
- `pnpm lint`
- PR #126 merge -> `main`
