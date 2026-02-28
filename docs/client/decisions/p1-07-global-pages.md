# feat: 글로벌 loading/error/not-found 페이지

> **Status**: draft
> **Type**: feat
> **Priority**: priority:1
> **Phase**: 1
> **Labels**: feat, priority:1
> **Depends on**: p1-01

## Goal

Next.js App Router의 글로벌 loading, error, not-found 페이지 구현

## Context

모든 페이지에서 공통으로 사용되는 로딩 스켈레톤, 에러 핸들링, 404 페이지.

- Plan reference: `docs/client/plans/phase-1-core.md` (Issue #7 → Task 6)

## Requirements

- `loading.tsx`: 스켈레톤 UI (글 목록 형태 placeholder 5개)
- `error.tsx`: 에러 메시지 + "다시 시도" 버튼 (use client)
- `not-found.tsx`: 404 + 홈으로 돌아가기 링크

## Scope

- Create: `src/app/loading.tsx`
- Create: `src/app/error.tsx`
- Create: `src/app/not-found.tsx`

## Definition of Done

- [ ] loading.tsx 스켈레톤 구현
- [ ] error.tsx 에러 페이지 구현
- [ ] not-found.tsx 404 페이지 구현
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
