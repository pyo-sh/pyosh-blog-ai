# feat: 조회수 기록 hook (sessionStorage)

> **Status**: draft
> **Type**: feat
> **Priority**: priority:2
> **Phase**: 3
> **Labels**: feat, priority:2

## Goal

글 조회수 기록 훅 + ViewCounter 컴포넌트 구현

## Context

글 상세 페이지에서 useEffect로 조회수 API 호출. sessionStorage로 같은 세션 내 중복 방지.

- Plan reference: `docs/client/plans/phase-3-public.md` (조회수 기록 섹션)

## Requirements

- `useViewCount(postId)`: sessionStorage에서 viewed_posts 확인 → 미조회 시 POST /api/stats/view 호출 → 조회 기록
- `ViewCounter`: useViewCount 호출 + null 렌더링 (use client)
- 글 상세 페이지에 `<ViewCounter postId={post.id} />` 추가

## Scope

- Create: `src/shared/hooks/use-view-count.ts`
- Create: `src/features/post-detail/ui/view-counter.tsx`
- Modify: `src/app/posts/[slug]/page.tsx`

## Definition of Done

- [ ] useViewCount 훅 구현 (sessionStorage 중복 방지)
- [ ] ViewCounter 컴포넌트 구현
- [ ] 글 상세 페이지 통합
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
