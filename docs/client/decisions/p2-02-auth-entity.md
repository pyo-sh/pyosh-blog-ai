# feat: Auth entity types + API

> **Status**: draft
> **Type**: feat
> **Priority**: priority:1
> **Phase**: 2
> **Labels**: feat, priority:1
> **Depends on**: p2-01

## Goal

관리자 인증 엔티티 타입과 API 함수 구현

## Context

Admin 로그인, 로그아웃, 세션 확인 API. 세션 쿠키 기반 인증.

- Plan reference: `docs/client/plans/phase-2-admin.md` (Issue #9 → Task 1)

## Requirements

- `AdminUser`: type, id, email, displayName
- `LoginCredentials`: email, password
- `login(credentials)`: POST /api/auth/admin/login
- `logout()`: POST /api/auth/admin/logout
- `fetchMe()`: GET /api/auth/me (client)
- `fetchMeServer(cookieHeader)`: GET /api/auth/me (server)

## Scope

- Create: `src/entities/auth/model.ts`
- Create: `src/entities/auth/api.ts`
- Create: `src/entities/auth/index.ts`

## Definition of Done

- [ ] AdminUser, LoginCredentials 타입 정의
- [ ] login, logout, fetchMe, fetchMeServer 함수 구현
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
