# Decision 003: Enforce CSRF on category and asset mutations

## Metadata
- **Date**: 2026-04-06
- **Status**: draft
- **Type**: bug
- **Area**: server

## Symptom

문서상 Category/Asset mutating API는 CSRF Required인데, 실제 구현은 `/api/admin/*` 일괄 hook 밖에 있어서 Category/Asset 일부 endpoint가 보호되지 않는다.

## Cause

전역 admin CSRF hook은 `server/src/app.ts`에서 `/api/admin/*` prefix에만 적용된다. Category와 Asset은 별도 public prefix 아래에 admin-protected route가 섞여 있어, route별 `onRequest: fastify.csrfProtection`가 빠진 곳은 문서와 실제가 어긋난다.

## Solution

- Category의 POST/PATCH/DELETE admin route에 명시적으로 CSRF를 건다.
- Asset의 DELETE route도 upload와 동일하게 명시적으로 CSRF를 건다.
- 필요한 route test를 추가/수정해 회귀를 막는다.

## Issue Draft
- **Type**: bug
- **Area**: server
- **Symptom**: Category/Asset mutation route가 문서와 달리 CSRF 없이 통과될 수 있다.
- **Cause**: `/api/admin/*` 전역 hook 범위 밖에 있는 route에 개별 CSRF hook이 빠져 있다.
- **Solution**: 누락된 route에 `fastify.csrfProtection`을 추가하고 테스트로 고정한다.
- **Dependencies**: 없음
- **Priority**: priority:1

## Template mapping

- `bug.yml`
- `area`: `server`
- `symptom`: Category/Asset mutation route CSRF 누락
- `cause`: `/api/admin/*` 범위 밖 route에 개별 hook 누락
- `solution`: route별 `fastify.csrfProtection` 추가와 test 보강
- `scope`: 아래 Scope 섹션 사용
- `dependencies`: `없음`
- `priority`: `priority:1`

## Scope

- Modify: `server/src/routes/categories/category.route.ts`
- Modify: `server/src/routes/assets/asset.route.ts`
- Modify: `server/test/routes/categories.test.ts`
- Modify: `server/test/routes/assets.test.ts`

## Acceptance criteria

- Category create/tree update/update/delete가 CSRF 없이 성공하지 않는다.
- Asset bulk delete/delete가 CSRF 없이 성공하지 않는다.
- 기존 admin session authorization 동작은 유지된다.
- route description과 실제 보안 동작이 더 이상 어긋나지 않는다.

## Verify

- `(cd server && pnpm test -- test/routes/categories.test.ts)`
- `(cd server && pnpm test -- test/routes/assets.test.ts)`
