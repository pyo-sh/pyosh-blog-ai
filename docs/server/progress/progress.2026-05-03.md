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
