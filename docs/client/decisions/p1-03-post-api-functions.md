# feat: Post API functions

> **Status**: draft
> **Type**: feat
> **Priority**: priority:1
> **Phase**: 1
> **Labels**: feat, priority:1
> **Depends on**: p1-02

## Goal

공개 Post 목록 조회 및 상세 조회 API 함수 구현

## Context

서버의 `GET /api/posts` (pagination, filter, search)와 `GET /api/posts/:slug` (with prevPost/nextPost) 엔드포인트를 호출하는 클라이언트 함수.

- Plan reference: `docs/client/plans/phase-1-core.md` (Issue #7 → Task 2)

## Requirements

- `fetchPosts(params, cookieHeader?)`: page, limit, categoryId, tagSlug, q 파라미터 지원
- `fetchPostBySlug(slug, cookieHeader?)`: 글 상세 + prevPost/nextPost 반환
- `serverFetch` 사용 (Server Component 호환)

## Scope

- Create: `src/entities/post/api.ts`
- Modify: `src/entities/post/index.ts`

## Definition of Done

- [ ] fetchPosts, fetchPostBySlug 함수 구현
- [ ] barrel export 업데이트
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
