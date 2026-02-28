# feat: 카테고리별 글 목록 페이지

> **Status**: draft
> **Type**: feat
> **Priority**: priority:1
> **Phase**: 1
> **Labels**: feat, priority:1
> **Depends on**: p1-04, p1-05, p1-13, p1-14

## Goal

`/categories/[slug]` 카테고리별 글 목록 페이지 구현 (SSR)

## Context

카테고리 slug로 카테고리를 찾고, categoryId로 글 목록 필터링. CategoryNav + PostCard + Pagination 재사용.

- Plan reference: `docs/client/plans/phase-1-core.md` (Issue #8 → Task 3)

## Requirements

- 재귀적 카테고리 탐색 (slug → category 매핑)
- 카테고리 없으면 notFound()
- CategoryNav (activeSlug 전달)
- PostCard 목록 + Pagination
- (선택) 홈 페이지에도 CategoryNav 추가

## Scope

- Create: `src/app/categories/[slug]/page.tsx`
- Modify: `src/app/page.tsx` (선택: CategoryNav 추가)

## Definition of Done

- [ ] 카테고리 페이지 SSR 구현
- [ ] 카테고리 탐색 + 404 처리
- [ ] CategoryNav + PostCard + Pagination 통합
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
