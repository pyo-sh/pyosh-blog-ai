# feat: PopularPost API

> **Status**: draft
> **Type**: feat
> **Priority**: priority:2
> **Phase**: 3
> **Labels**: feat, priority:2

## Goal

인기 글 조회 API 함수 구현

## Context

`GET /api/stats/popular?days=7&limit=10` → `{ data: [{ postId, slug, title, pageviews, uniques }] }`.

- Plan reference: `docs/client/plans/phase-3-public.md` (Issue #16 → Task 1)

## Requirements

- `PopularPost`: postId, slug, title, pageviews, uniques
- `fetchPopularPosts(days, cookieHeader?)`: serverFetch
- entities/stat에 추가

## Scope

- Modify: `src/entities/stat/model.ts`
- Modify: `src/entities/stat/api.ts`
- Modify: `src/entities/stat/index.ts`

## Definition of Done

- [ ] PopularPost 타입 + fetchPopularPosts 함수 구현
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
