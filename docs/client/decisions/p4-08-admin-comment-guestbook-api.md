# feat: Admin 댓글/방명록 API functions

> **Status**: draft
> **Type**: feat
> **Priority**: priority:3
> **Phase**: 4
> **Labels**: feat, priority:3

## Goal

Admin 댓글 및 방명록 관리 API 함수 구현

## Context

관리자가 댓글/방명록을 조회하고 강제 삭제할 수 있는 API. 비밀 댓글 내용 확인 가능.

- Plan reference: `docs/client/plans/phase-4-extras.md` (Admin 댓글/방명록 관리 → Task 1)

## Requirements

- `AdminCommentItem`: id, postId, parentId, depth, body, isSecret, status, author, replyToName, createdAt, updatedAt
- `fetchAdminComments(params)`: page, postId 필터
- `adminDeleteComment(id)`: 강제 삭제
- `fetchAdminGuestbook(page)`: 관리자 방명록 목록
- `adminDeleteGuestbookEntry(id)`: 강제 삭제

## Scope

- Modify: `src/entities/comment/api.ts`
- Modify: `src/entities/guestbook/api.ts`

## Definition of Done

- [ ] Admin 댓글 API 함수 추가
- [ ] Admin 방명록 API 함수 추가
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
