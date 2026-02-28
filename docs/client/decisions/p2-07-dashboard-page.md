# feat: Admin 대시보드 페이지

> **Status**: draft
> **Type**: feat
> **Priority**: priority:1
> **Phase**: 2
> **Labels**: feat, priority:1
> **Depends on**: p2-04, p2-06

## Goal

`/dashboard` 관리자 대시보드 페이지 구현

## Context

통계 카드 (조회수, 게시글, 댓글) + 반응형 그리드. TanStack Query로 데이터 페칭.

- Plan reference: `docs/client/plans/phase-2-admin.md` (Issue #10 → Task 2)

## Requirements

- use client + TanStack Query
- 통계 카드 5개: 오늘/주간/월간 조회수, 총 게시글, 총 댓글
- 로딩 스켈레톤
- 반응형 그리드 (2열 → 3열 → 5열)

## Scope

- Create: `src/app/dashboard/page.tsx`

## Definition of Done

- [ ] 대시보드 페이지 구현 (TanStack Query)
- [ ] 통계 카드 5개 표시
- [ ] 로딩 상태 스켈레톤
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
