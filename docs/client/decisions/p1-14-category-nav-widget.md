# feat: CategoryNav 위젯

> **Status**: draft
> **Type**: feat
> **Priority**: priority:1
> **Phase**: 1
> **Labels**: feat, priority:1
> **Depends on**: p1-13

## Goal

카테고리 네비게이션 위젯 (pill 형태 카테고리 목록)

## Context

홈, 카테고리 페이지에서 카테고리 필터 역할. widgets 계층에 배치.

- Plan reference: `docs/client/plans/phase-1-core.md` (Issue #8 → Task 2)

## Requirements

- 전체 + 각 카테고리 pill 링크
- activeSlug에 따라 선택 상태 하이라이트
- `/categories/[slug]` 링크

## Scope

- Create: `src/widgets/category-nav/ui/category-nav.tsx`
- Create: `src/widgets/category-nav/index.ts`

## Definition of Done

- [ ] CategoryNav 컴포넌트 구현
- [ ] barrel export 설정
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
