# feat: Admin 글 목록 페이지

> **Status**: draft
> **Type**: feat
> **Priority**: priority:1
> **Phase**: 2
> **Labels**: feat, priority:1
> **Depends on**: p2-04, p2-08

## Goal

`/dashboard/posts` 관리자 글 목록 관리 페이지 구현

## Context

모든 상태의 글 관리. 필터(상태, 삭제 포함), 페이지네이션, 삭제/복원 액션.

- Plan reference: `docs/client/plans/phase-2-admin.md` (Issue #11 → Task 2)

## Requirements

- use client + TanStack Query
- 필터: 상태 드롭다운 (전체/초안/발행/보관), 삭제된 글 포함 체크박스
- 테이블: 제목(편집 링크), 상태, 가시성, 작성일, 작업(삭제/복원)
- 클라이언트 페이지네이션
- "새 글 작성" 버튼 → /dashboard/posts/new

## Scope

- Create: `src/app/dashboard/posts/page.tsx`

## Definition of Done

- [ ] Admin 글 목록 페이지 구현
- [ ] 상태 필터 + 삭제 포함 필터 동작
- [ ] 삭제/복원 mutation 동작
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
