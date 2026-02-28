# feat: Admin 댓글 관리 페이지

> **Status**: draft
> **Type**: feat
> **Priority**: priority:3
> **Phase**: 4
> **Labels**: feat, priority:3
> **Depends on**: p4-08

## Goal

`/dashboard/comments` 관리자 댓글 관리 페이지 구현

## Context

모든 댓글 (비밀 포함) 조회 + 강제 삭제. TanStack Query 사용.

- Plan reference: `docs/client/plans/phase-4-extras.md` (Admin 댓글/방명록 관리 → Task 2)

## Requirements

- use client + TanStack Query
- 테이블: 작성자, 내용 (truncate), 비밀 여부, 작성일, 삭제 버튼
- 클라이언트 페이지네이션
- 강제 삭제 mutation

## Scope

- Create: `src/app/dashboard/comments/page.tsx`

## Definition of Done

- [ ] Admin 댓글 관리 페이지 구현
- [ ] 강제 삭제 동작
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
