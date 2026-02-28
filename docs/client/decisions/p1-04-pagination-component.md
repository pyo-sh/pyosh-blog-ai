# feat: Pagination 공통 컴포넌트

> **Status**: draft
> **Type**: feat
> **Priority**: priority:1
> **Phase**: 1
> **Labels**: feat, priority:1
> **Depends on**: p1-01

## Goal

페이지 번호 기반 Pagination 공통 컴포넌트 구현

## Context

홈, 카테고리, 태그, 검색, Admin 목록 등 다수 페이지에서 재사용. shared/ui 계층에 배치.

- Plan reference: `docs/client/plans/phase-1-core.md` (Issue #7 → Task 3)

## Requirements

- Props: currentPage, totalPages, basePath, queryParams
- totalPages ≤ 1이면 렌더링 안 함
- 이전/다음 버튼 + 페이지 번호 링크
- Next.js Link 컴포넌트 사용
- queryParams 지원 (검색 등에서 사용)

## Scope

- Create: `src/shared/ui/libs/pagination.tsx`
- Modify: `src/shared/ui/libs/index.tsx`

## Definition of Done

- [ ] Pagination 컴포넌트 구현
- [ ] shared/ui barrel export 추가
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
