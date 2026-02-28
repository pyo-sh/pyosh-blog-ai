# feat: Admin 방명록 관리 페이지

> **Status**: draft
> **Type**: feat
> **Priority**: priority:3
> **Phase**: 4
> **Labels**: feat, priority:3
> **Depends on**: p4-08

## Goal

`/dashboard/guestbook` 관리자 방명록 관리 페이지 구현

## Context

댓글 관리 페이지와 동일 패턴. fetchAdminGuestbook + adminDeleteGuestbookEntry 사용.

- Plan reference: `docs/client/plans/phase-4-extras.md` (Admin 댓글/방명록 관리 → Task 3)

## Requirements

- 댓글 관리 페이지와 동일 패턴
- 테이블: 작성자, 내용, 비밀 여부, 작성일, 삭제 버튼
- 클라이언트 페이지네이션

## Scope

- Create: `src/app/dashboard/guestbook/page.tsx`

## Definition of Done

- [ ] Admin 방명록 관리 페이지 구현
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
