# feat: Category Admin API functions

> **Status**: draft
> **Type**: feat
> **Priority**: priority:3
> **Phase**: 4
> **Labels**: feat, priority:3

## Goal

Admin 카테고리 CRUD + 순서 변경 API 함수 구현

## Context

카테고리 관리 페이지에서 사용. hidden 포함 전체 조회, 생성, 수정, 순서 변경, 삭제.

- Plan reference: `docs/client/plans/phase-4-extras.md` (Issue #17 → Task 1)

## Requirements

- `CreateCategoryBody`: name, parentId?, isVisible?
- `UpdateCategoryBody`: name?, isVisible?
- `UpdateCategoryOrderBody`: orders[{ id, sortOrder }]
- `fetchCategoriesAdmin()`: include_hidden=true
- `createCategory(body)`, `updateCategory(id, body)`, `updateCategoryOrder(body)`, `deleteCategory(id)`

## Scope

- Modify: `src/entities/category/model.ts`
- Modify: `src/entities/category/api.ts`
- Modify: `src/entities/category/index.ts`

## Definition of Done

- [ ] Admin 카테고리 API 함수 구현
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
