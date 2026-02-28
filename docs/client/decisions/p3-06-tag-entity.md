# feat: Tag entity types + API

> **Status**: draft
> **Type**: feat
> **Priority**: priority:2
> **Phase**: 3
> **Labels**: feat, priority:2

## Goal

태그 엔티티 타입과 API 함수 구현

## Context

`GET /api/tags` → `{ tags: [{ id, name, slug, postCount }] }`. 태그 목록 + 글 수 표시.

- Plan reference: `docs/client/plans/phase-3-public.md` (Issue #15 → Task 1)

## Requirements

- `Tag`: id, name, slug, postCount
- `fetchTags(cookieHeader?)`: serverFetch

## Scope

- Create: `src/entities/tag/model.ts`
- Create: `src/entities/tag/api.ts`
- Create: `src/entities/tag/index.ts`

## Definition of Done

- [ ] Tag 타입 + fetchTags 함수 구현
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
