# feat: Post create/update API functions

> **Status**: draft
> **Type**: feat
> **Priority**: priority:1
> **Phase**: 2
> **Labels**: feat, priority:1
> **Depends on**: p2-01

## Goal

글 생성/수정/개별조회 API 함수 구현

## Context

에디터에서 사용할 API. POST /api/admin/posts, PATCH /api/admin/posts/:id, GET /api/admin/posts/:id.

- Plan reference: `docs/client/plans/phase-2-admin.md` (Issue #12 → Task 1)

## Requirements

- `CreatePostBody`: title, contentMd, categoryId, thumbnailUrl?, visibility?, status?, tags?, publishedAt?
- `UpdatePostBody`: 모든 필드 optional
- `fetchAdminPost(id)`: 글 상세 조회
- `createPost(body)`: 글 생성
- `updatePost(id, body)`: 글 수정

## Scope

- Modify: `src/entities/post/model.ts`
- Modify: `src/entities/post/api.ts`
- Modify: `src/entities/post/index.ts`

## Definition of Done

- [ ] CreatePostBody, UpdatePostBody 타입 정의
- [ ] fetchAdminPost, createPost, updatePost 함수 구현
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
