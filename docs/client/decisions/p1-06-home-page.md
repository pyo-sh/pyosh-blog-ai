# feat: 홈 페이지 (SSR)

> **Status**: draft
> **Type**: feat
> **Priority**: priority:1
> **Phase**: 1
> **Labels**: feat, priority:1
> **Depends on**: p1-03, p1-04, p1-05

## Goal

블로그 홈 페이지를 Server Component(SSR)로 구현, 글 목록 + 페이지네이션

## Context

`GET /api/posts?page=N`으로 최신 글 목록을 SSR 렌더링. PostCard와 Pagination 컴포넌트 재사용.

- Plan reference: `docs/client/plans/phase-1-core.md` (Issue #7 → Task 5)

## Requirements

- `src/app/page.tsx`를 Server Component로 구현
- searchParams에서 page 파라미터 추출
- fetchPosts 호출 → PostCard 목록 + Pagination 렌더링
- 게시글 없을 때 안내 메시지 표시

## Scope

- Modify: `src/app/page.tsx`

## Definition of Done

- [ ] 홈 페이지 SSR 구현
- [ ] 페이지네이션 동작 확인
- [ ] 빈 상태 처리
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
