# feat: Category entity types + API

> **Status**: draft
> **Type**: feat
> **Priority**: priority:1
> **Phase**: 1
> **Labels**: feat, priority:1
> **Depends on**: p1-01

## Goal

Category 엔티티 타입과 공개 API 함수 구현

## Context

카테고리 트리 구조. `GET /api/categories` → 재귀적 children 포함.

- Plan reference: `docs/client/plans/phase-1-core.md` (Issue #8 → Task 1)

## Requirements

- `Category` 인터페이스: id, parentId, name, slug, sortOrder, isVisible, createdAt, updatedAt, children (재귀)
- `fetchCategories(cookieHeader?)`: 카테고리 트리 반환
- serverFetch 사용

## Scope

- Create: `src/entities/category/model.ts`
- Create: `src/entities/category/api.ts`
- Create: `src/entities/category/index.ts`

## Definition of Done

- [ ] Category 타입 + API 함수 구현
- [ ] barrel export 설정
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
