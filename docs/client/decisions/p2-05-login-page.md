# feat: Admin 로그인 페이지

> **Status**: draft
> **Type**: feat
> **Priority**: priority:1
> **Phase**: 2
> **Labels**: feat, priority:1
> **Depends on**: p2-02, p2-04

## Goal

`/dashboard/login` 관리자 로그인 페이지 구현

## Context

독립 레이아웃 (사이드바 없음). 이메일/비밀번호 폼. 로그인 성공 시 /dashboard로 이동.

- Plan reference: `docs/client/plans/phase-2-admin.md` (Issue #9 → Task 4)

## Requirements

- LoginForm (use client): email, password, error 상태, loading 상태
- login() API 호출 → 성공 시 router.push + router.refresh
- 실패 시 에러 메시지 표시
- login/layout.tsx: 별도 레이아웃 (사이드바 없이)

## Scope

- Create: `src/features/admin-login/ui/login-form.tsx`
- Create: `src/features/admin-login/index.ts`
- Create: `src/app/dashboard/login/page.tsx`
- Create: `src/app/dashboard/login/layout.tsx`

## Definition of Done

- [ ] LoginForm 컴포넌트 구현
- [ ] 로그인 페이지 + 독립 레이아웃
- [ ] 로그인/에러 동작 확인
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
