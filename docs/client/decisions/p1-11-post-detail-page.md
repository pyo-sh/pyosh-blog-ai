# feat: 글 상세 페이지 (SSR)

> **Status**: draft
> **Type**: feat
> **Priority**: priority:1
> **Phase**: 1
> **Labels**: feat, priority:1
> **Depends on**: p1-03, p1-10

## Goal

`/posts/[slug]` 글 상세 페이지를 Server Component로 구현

## Context

서버에서 fetchPostBySlug로 글 데이터를 가져와 SSR. 헤더(제목, 카테고리, 날짜, 태그), 썸네일(next/image), PostContent, PostNavigation 조합.

- Plan reference: `docs/client/plans/phase-1-core.md` (Issue #5 → Task 4)

## Requirements

- 404 처리: ApiResponseError 404 → notFound()
- 헤더: 제목, 카테고리 링크, 날짜, 태그 링크
- 썸네일: next/image (fill, priority)
- 본문: PostContent (async Server Component)
- 이전/다음: PostNavigation
- `next.config.js` remotePatterns에 localhost:5500 추가

## Scope

- Create: `src/app/posts/[slug]/page.tsx`
- Modify: `next.config.js`

## Definition of Done

- [ ] 글 상세 페이지 SSR 구현
- [ ] 404 처리
- [ ] next.config.js remotePatterns 업데이트
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
