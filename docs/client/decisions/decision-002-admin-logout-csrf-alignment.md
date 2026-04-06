# Decision 002: Align admin logout client call with CSRF contract

## Metadata
- **Date**: 2026-04-06
- **Status**: draft
- **Type**: bug
- **Area**: client

## Symptom

`POST /api/auth/admin/logout`는 서버에서 CSRF를 요구하지만, 클라이언트는 CSRF 토큰 없이 호출한다.

## Cause

logout helper가 `clientMutate`가 아니라 `clientFetch`를 사용한다.

## Solution

logout 호출을 다른 mutation API와 동일한 방식으로 바꾸고, 관리자 사이드바 로그아웃 흐름이 그대로 유지되도록 맞춘다.

## Issue Draft
- **Type**: bug
- **Area**: client
- **Symptom**: 관리자 로그아웃이 CSRF 계약과 다르게 동작한다.
- **Cause**: logout helper가 CSRF 헤더를 붙이지 않는다.
- **Solution**: logout API helper를 mutation 경로로 바꾼다.
- **Dependencies**: 없음
- **Priority**: priority:1

## Template mapping

- `bug.yml`
- `area`: `client`
- `symptom`: logout 요청이 CSRF 없이 전송됨
- `cause`: logout helper가 `clientFetch` 사용
- `solution`: `clientMutate` 또는 동일 수준의 CSRF 포함 호출로 변경
- `scope`: 아래 Scope 섹션 사용
- `dependencies`: `없음`
- `priority`: `priority:1`

## Scope

- Modify: `client/src/entities/auth/api.ts`
- Review: `client/src/widgets/admin-sidebar/ui/admin-sidebar.tsx`
- Review: `client/src/shared/api/mutation.ts`

## Acceptance criteria

- logout helper가 CSRF 토큰을 포함한다.
- 관리 화면에서 로그아웃 시 403 없이 세션이 종료된다.
- 호출부 수정이 최소화된다.
- auth helper naming과 usage가 다른 mutation helper 패턴과 일관된다.

## Verify

- `(cd client && pnpm compile:types && pnpm lint && pnpm build)`
