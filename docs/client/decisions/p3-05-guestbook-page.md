# feat: 방명록 페이지

> **Status**: draft
> **Type**: feat
> **Priority**: priority:2
> **Phase**: 3
> **Labels**: feat, priority:2
> **Depends on**: p3-04

## Goal

`/guestbook` 방명록 페이지 구현

## Context

SSR 초기 로드 + CommentForm 재사용. 게스트 작성, 삭제(비밀번호), 페이지네이션.

- Plan reference: `docs/client/plans/phase-3-public.md` (Issue #14 → Task 2)

## Requirements

- GuestbookPageContent (use client): 방명록 목록 + CommentForm 재사용 + 삭제 모달
- SSR 페이지: fetchGuestbook → GuestbookPageContent + Pagination
- CommentForm을 방명록에서도 재사용

## Scope

- Create: `src/features/guestbook-form/ui/guestbook-page-content.tsx`
- Create: `src/features/guestbook-form/index.ts`
- Create: `src/app/guestbook/page.tsx`

## Definition of Done

- [ ] GuestbookPageContent 구현
- [ ] 방명록 SSR 페이지 구현
- [ ] CommentForm 재사용
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
