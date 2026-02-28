# feat: Stat entity (대시보드)

> **Status**: draft
> **Type**: feat
> **Priority**: priority:1
> **Phase**: 2
> **Labels**: feat, priority:1
> **Depends on**: p2-01

## Goal

대시보드 통계 엔티티 타입과 API 함수 구현

## Context

Admin 대시보드에서 표시할 통계 데이터. `GET /api/admin/stats/dashboard`.

- Plan reference: `docs/client/plans/phase-2-admin.md` (Issue #10 → Task 1)

## Requirements

- `DashboardStats`: todayPageviews, weekPageviews, monthPageviews, totalPosts, totalComments
- `fetchDashboardStats()`: clientFetch 사용

## Scope

- Create: `src/entities/stat/model.ts`
- Create: `src/entities/stat/api.ts`
- Create: `src/entities/stat/index.ts`

## Definition of Done

- [ ] DashboardStats 타입 + API 함수 구현
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
