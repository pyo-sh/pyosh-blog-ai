# feat: Post entity types 정의

> **Status**: draft
> **Type**: feat
> **Priority**: priority:1
> **Phase**: 1
> **Labels**: feat, priority:1
> **Depends on**: p1-01

## Goal

Post, PostTag, PostCategory, PostNavigation 타입을 entities/post/ 계층에 정의

## Context

홈 페이지, 글 상세, 카테고리 등 다수 기능에서 사용하는 핵심 엔티티. FSD 아키텍처의 entities 계층에 배치.

- Plan reference: `docs/client/plans/phase-1-core.md` (Issue #7 → Task 1)

## Requirements

- `Post` 인터페이스: id, categoryId, title, slug, contentMd, thumbnailUrl, visibility, status, publishedAt, createdAt, updatedAt, deletedAt, category, tags
- `PostTag` 인터페이스: id, name, slug
- `PostCategory` 인터페이스: id, name, slug
- `PostNavigation` 인터페이스: slug, title
- barrel export (`index.ts`)

## Scope

- Create: `src/entities/post/model.ts`
- Create: `src/entities/post/index.ts`

## Definition of Done

- [ ] Post, PostTag, PostCategory, PostNavigation 타입 정의
- [ ] barrel export 설정
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
