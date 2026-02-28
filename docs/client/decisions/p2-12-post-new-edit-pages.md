# feat: 글 작성/수정 페이지

> **Status**: draft
> **Type**: feat
> **Priority**: priority:1
> **Phase**: 2
> **Labels**: feat, priority:1
> **Depends on**: p2-04, p2-11

## Goal

`/dashboard/posts/new` 글 작성 페이지와 `/dashboard/posts/[id]/edit` 글 수정 페이지 구현

## Context

새 글 작성 페이지는 빈 PostForm, 수정 페이지는 기존 글 데이터로 초기화된 PostForm 렌더링.

- Plan reference: `docs/client/plans/phase-2-admin.md` (Issue #12 → Task 3)

## Requirements

- 새 글: PostForm 렌더링
- 수정: useParams로 id 추출, fetchAdminPost로 기존 글 로드, PostForm에 전달
- 수정 시 로딩 상태 처리

## Scope

- Create: `src/app/dashboard/posts/new/page.tsx`
- Create: `src/app/dashboard/posts/[id]/edit/page.tsx`

## Definition of Done

- [ ] 새 글 작성 페이지 구현
- [ ] 글 수정 페이지 구현 (기존 데이터 로드)
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
