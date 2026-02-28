# feat: Next.js middleware (/dashboard/* 인증 보호)

> **Status**: draft
> **Type**: feat
> **Priority**: priority:1
> **Phase**: 2
> **Labels**: feat, priority:1
> **Depends on**: p2-02

## Goal

`/dashboard/*` 경로에 대한 인증 미들웨어 구현

## Context

미인증 사용자가 Admin 페이지 접근 시 `/dashboard/login`으로 리다이렉트. `/dashboard/login`은 보호 대상 아님.

- Plan reference: `docs/client/plans/phase-2-admin.md` (Issue #9 → Task 2)

## Requirements

- `src/middleware.ts`에서 `/dashboard/:path*` 매칭
- `/dashboard/login`은 통과
- 쿠키를 서버 `/api/auth/me`로 전달하여 인증 확인
- 실패 시 `/dashboard/login`으로 redirect

## Scope

- Create: `src/middleware.ts`

## Definition of Done

- [ ] middleware 구현 (matcher: /dashboard/:path*)
- [ ] /dashboard/login 예외 처리
- [ ] 인증 실패 → 로그인 리다이렉트
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
