# feat: Admin Post API functions

> **Status**: draft
> **Type**: feat
> **Priority**: priority:1
> **Phase**: 2
> **Labels**: feat, priority:1
> **Depends on**: p2-01

## Goal

Admin 글 목록 조회, 삭제, 복원, 하드 삭제 API 함수 구현

## Context

관리자 글 관리에 필요한 API. clientFetch + clientMutate 사용.

- Plan reference: `docs/client/plans/phase-2-admin.md` (Issue #11 → Task 1)

## Requirements

- `fetchAdminPosts(params)`: page, limit, status, visibility, categoryId, includeDeleted, q
- `deletePost(id)`: DELETE /api/admin/posts/:id (soft)
- `restorePost(id)`: PUT /api/admin/posts/:id/restore
- `hardDeletePost(id)`: DELETE /api/admin/posts/:id/hard

## Scope

- Modify: `src/entities/post/api.ts`
- Modify: `src/entities/post/index.ts`

## Definition of Done

- [ ] fetchAdminPosts, deletePost, restorePost, hardDeletePost 구현
- [ ] barrel export 업데이트
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
