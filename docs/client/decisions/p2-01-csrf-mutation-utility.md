# feat: CSRF 토큰 유틸리티 + mutation helper

> **Status**: draft
> **Type**: feat
> **Priority**: priority:1
> **Phase**: 2
> **Labels**: feat, priority:1

## Goal

CSRF 토큰 관리 유틸리티와 mutation 헬퍼 함수 구현

## Context

서버는 POST/PUT/PATCH/DELETE 요청에 `x-csrf-token` 헤더를 요구. Phase 2에서 mutation이 처음 발생하므로 여기서 구현. `GET /api/auth/csrf-token` → `{ token }`.

- Plan reference: `docs/client/plans/phase-2-admin.md` (Prerequisite 섹션)

## Requirements

- `getCsrfToken()`: 토큰 캐싱 + lazy fetch
- `clearCsrfToken()`: 토큰 초기화 (로그아웃 시)
- `clientMutate<T>(path, options)`: clientFetch + CSRF 토큰 자동 주입

## Scope

- Create: `src/shared/api/csrf.ts`
- Create: `src/shared/api/mutation.ts`
- Modify: `src/shared/api/index.ts`

## Definition of Done

- [ ] getCsrfToken, clearCsrfToken 구현
- [ ] clientMutate 함수 구현
- [ ] barrel export 업데이트
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
