# feat: PostCard 컴포넌트

> **Status**: draft
> **Type**: feat
> **Priority**: priority:1
> **Phase**: 1
> **Labels**: feat, priority:1
> **Depends on**: p1-02, p1-03

## Goal

글 목록에서 사용하는 PostCard 컴포넌트 구현

## Context

홈, 카테고리, 태그, 검색 페이지에서 재사용되는 글 카드. features/post-list 계층.

- Plan reference: `docs/client/plans/phase-1-core.md` (Issue #7 → Task 4)

## Requirements

- 썸네일 (next/image, 데스크톱만 192px), 제목, 요약 (contentMd 200자 plain text), 카테고리, 날짜, 태그 표시
- 반응형: 모바일에서 썸네일 숨김
- `/posts/[slug]` 링크

## Scope

- Create: `src/features/post-list/ui/post-card.tsx`
- Create: `src/features/post-list/index.ts`

## Definition of Done

- [ ] PostCard 컴포넌트 구현 (썸네일, 제목, 요약, 카테고리, 날짜, 태그)
- [ ] barrel export 설정
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
