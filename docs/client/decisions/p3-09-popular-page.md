# feat: 인기 글 페이지

> **Status**: draft
> **Type**: feat
> **Priority**: priority:2
> **Phase**: 3
> **Labels**: feat, priority:2
> **Depends on**: p3-08

## Goal

`/popular` 인기 글 페이지 구현 (기간 필터 탭)

## Context

조회수 기반 랭킹. 7일/30일 기간 필터. 순위 번호 + pageviews + uniques 표시.

- Plan reference: `docs/client/plans/phase-3-public.md` (Issue #16 → Task 2)

## Requirements

- SSR 페이지
- 기간 셀렉터: 7일 / 30일 (URL 파라미터 days)
- 순위 번호 + 제목 (링크) + views/visitors 통계

## Scope

- Create: `src/app/popular/page.tsx`

## Definition of Done

- [ ] 인기 글 페이지 구현 (SSR)
- [ ] 기간 필터 동작
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
