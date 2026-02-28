# feat: 태그 목록 + 태그별 글 목록 페이지

> **Status**: draft
> **Type**: feat
> **Priority**: priority:2
> **Phase**: 3
> **Labels**: feat, priority:2
> **Depends on**: p3-06

## Goal

`/tags` 태그 목록 페이지와 `/tags/[slug]` 태그별 글 목록 페이지 구현

## Context

태그 클라우드/리스트 (글 수 표시). 태그별 글 목록은 PostCard + Pagination 재사용.

- Plan reference: `docs/client/plans/phase-3-public.md` (Issue #15 → Task 2)

## Requirements

- `/tags`: 전체 태그 pill 링크 (name + postCount)
- `/tags/[slug]`: fetchPosts({ tagSlug }) → PostCard + Pagination

## Scope

- Create: `src/app/tags/page.tsx`
- Create: `src/app/tags/[slug]/page.tsx`

## Definition of Done

- [ ] 태그 목록 페이지 구현
- [ ] 태그별 글 목록 페이지 구현
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
