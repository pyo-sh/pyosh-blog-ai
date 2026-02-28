# feat: 카테고리 관리 feature + 페이지

> **Status**: draft
> **Type**: feat
> **Priority**: priority:3
> **Phase**: 4
> **Labels**: feat, priority:3
> **Depends on**: p4-01

## Goal

`/dashboard/categories` 카테고리 관리 페이지 (트리 시각화, CRUD 모달)

## Context

카테고리 트리 시각화 + 추가/수정 모달 + 삭제 확인. TanStack Query 사용.

- Plan reference: `docs/client/plans/phase-4-extras.md` (Issue #17 → Task 2)

## Requirements

- CategoryTree: 재귀 트리 렌더링, 수정/삭제 버튼, hidden 표시
- CategoryFormModal: 이름, 부모 카테고리 선택, 표시 여부 체크
- Admin 카테고리 페이지: TanStack Query + mutations

## Scope

- Create: `src/features/category-manager/ui/category-tree.tsx`
- Create: `src/features/category-manager/ui/category-form-modal.tsx`
- Create: `src/features/category-manager/index.ts`
- Create: `src/app/dashboard/categories/page.tsx`

## Definition of Done

- [ ] CategoryTree 컴포넌트 구현
- [ ] CategoryFormModal 구현
- [ ] 카테고리 관리 페이지 구현
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
