# feat: 글 상세 페이지 댓글 통합

> **Status**: draft
> **Type**: feat
> **Priority**: priority:2
> **Phase**: 3
> **Labels**: feat, priority:2
> **Depends on**: p3-02

## Goal

글 상세 페이지 하단에 CommentList 통합

## Context

SSR로 초기 댓글 fetch, CommentList에 initialComments로 전달.

- Plan reference: `docs/client/plans/phase-3-public.md` (Issue #13 → Task 3)

## Requirements

- `src/app/posts/[slug]/page.tsx`에서 `fetchComments(post.id)` 추가
- `<CommentList postId={post.id} initialComments={comments} />` 렌더링

## Scope

- Modify: `src/app/posts/[slug]/page.tsx`

## Definition of Done

- [ ] 글 상세 페이지에 댓글 통합
- [ ] SSR 초기 로드 동작
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
