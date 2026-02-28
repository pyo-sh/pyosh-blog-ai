# feat: Comment entity types + API

> **Status**: draft
> **Type**: feat
> **Priority**: priority:2
> **Phase**: 3
> **Labels**: feat, priority:2

## Goal

댓글 엔티티 타입과 API 함수 구현 (게스트 전용)

## Context

계층형 댓글. 게스트 댓글 (이름, 이메일, 비밀번호). 비밀 댓글 지원. 서버 스키마: `CommentDetailSchema`, `CreateCommentGuestBodySchema`.

- Plan reference: `docs/client/plans/phase-3-public.md` (Issue #13 → Task 1)

## Requirements

- `CommentAuthor`: type (oauth|guest), id?, name, email?, avatarUrl?
- `Comment`: id, postId, parentId, depth, body, isSecret, status, author, replyToName, replies (재귀), createdAt, updatedAt
- `CreateCommentGuestBody`: body, parentId?, replyToCommentId?, isSecret?, guestName, guestEmail, guestPassword
- `DeleteCommentGuestBody`: guestPassword
- `fetchComments(postId, cookieHeader?)`: serverFetch
- `createComment(postId, body)`: clientMutate
- `deleteComment(commentId, body)`: clientMutate

## Scope

- Create: `src/entities/comment/model.ts`
- Create: `src/entities/comment/api.ts`
- Create: `src/entities/comment/index.ts`

## Definition of Done

- [ ] Comment 타입 + API 함수 구현
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
