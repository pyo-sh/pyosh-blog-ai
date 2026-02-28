# feat: 검색 결과 페이지 (SSR)

> **Status**: draft
> **Type**: feat
> **Priority**: priority:3
> **Phase**: 4
> **Labels**: feat, priority:3

## Goal

`/search?q=keyword` 검색 결과 페이지 구현

## Context

기존 `GET /api/posts?q=keyword` API 활용. SSR. PostCard + Pagination 재사용.

- Plan reference: `docs/client/plans/phase-4-extras.md` (검색 기능 섹션)

## Requirements

- SSR 페이지: searchParams에서 q, page 추출
- q 없으면 안내 메시지
- fetchPosts({ q, page }) → PostCard 목록 + Pagination
- 결과 수 표시 (meta.total)

## Scope

- Create: `src/app/search/page.tsx`

## Definition of Done

- [ ] 검색 결과 페이지 SSR 구현
- [ ] 빈 쿼리/결과 없음 처리
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
