# feat: Guestbook entity types + API

> **Status**: draft
> **Type**: feat
> **Priority**: priority:2
> **Phase**: 3
> **Labels**: feat, priority:2

## Goal

방명록 엔티티 타입과 API 함수 구현

## Context

댓글과 유사한 구조. 게스트 작성, 비밀글, 삭제(비밀번호). CommentAuthor 타입 재사용.

- Plan reference: `docs/client/plans/phase-3-public.md` (Issue #14 → Task 1)

## Requirements

- `GuestbookEntry`: id, parentId, body, isSecret, status, author(CommentAuthor), replies, createdAt, updatedAt
- `CreateGuestbookBody`: body, parentId?, isSecret?, guestName, guestEmail, guestPassword
- `DeleteGuestbookBody`: guestPassword
- `fetchGuestbook(page, cookieHeader?)`: serverFetch (PaginatedResponse)
- `createGuestbookEntry(body)`: clientMutate
- `deleteGuestbookEntry(id, body)`: clientMutate

## Scope

- Create: `src/entities/guestbook/model.ts`
- Create: `src/entities/guestbook/api.ts`
- Create: `src/entities/guestbook/index.ts`

## Definition of Done

- [ ] Guestbook 타입 + API 함수 구현
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
