# Decision 002: Change admin auth route contract to username

## Metadata
- **Date**: 2026-04-06
- **Status**: draft
- **Type**: feature
- **Area**: server

## Goal

Admin auth API 계약을 `email`이 아닌 `username` 기준으로 바꾼다.

## Context

Persistence 레이어 정리만으로는 충분하지 않다. 외부 계약인 `POST /api/auth/admin/login`과 `GET /api/auth/me`도 `username` 기반으로 노출되어야 client와 docs가 같은 용어를 사용한다.

루트 `docs/server/api-spec.md` 갱신은 이 작업의 직접 범위는 아니지만, 이 계약 변경이 머지된 후 후속 docs 작업에서 반드시 반영되어야 한다.

## Issue Draft
- **Type**: feature
- **Area**: server
- **Goal**: Admin auth request/response contract를 `username` 기준으로 전환한다.
- **Dependencies**:
  - `docs/server/decisions/decision-001-admin-persistence-rename-email-to-username.md`
- **Priority**: priority:1

## Template mapping

- `feature.yml`
- `area`: `server`
- `goal`: Admin auth API 계약을 `username` 기준으로 전환
- `context`: workspace decision과 persistence rename 이후 외부 API 계약도 동일 용어를 써야 함
- `requirements`: 아래 Requirements 섹션 사용
- `scope`: 아래 Scope 섹션 사용
- `dependencies`: 아래 Dependencies 섹션 사용
- `priority`: `priority:1`

## Scope

- Modify: `server/src/routes/auth/auth.route.ts`
- Modify: `server/test/routes/auth.test.ts`
- Modify if needed: `server/src/types/fastify.d.ts`

## Requirements

- `POST /api/auth/admin/login` request body는 `{ username, password }`
- login request의 `username`은 최소 4자이다
- login request의 `username`은 최대 20자이다
- `username`은 모든 언어 문자, 숫자, `_`, `-`, `.`만 허용한다
- 앞뒤 공백과 내부 공백은 모두 허용하지 않는다
- 입력값을 `trim`하여 보정하지 않는다
- login request에 이메일 형식 검증을 적용하지 않는다
- login response의 admin object도 `username` 필드를 반환
- `GET /api/auth/me`의 admin 응답도 `username` 필드를 반환
- 인증 실패 메시지도 `username or password` 기준으로 정리
- schema/summary/description/example에서 legacy `email` 표현을 제거한다

## Response shape examples

### `POST /api/auth/admin/login`

```json
{
  "admin": {
    "id": 1,
    "username": "관리자-01",
    "createdAt": "ISO-8601",
    "updatedAt": "ISO-8601",
    "lastLoginAt": "ISO-8601 | null"
  }
}
```

### `GET /api/auth/me` for admin

```json
{
  "type": "admin",
  "id": 1,
  "username": "관리자-01",
  "createdAt": "ISO-8601",
  "updatedAt": "ISO-8601",
  "lastLoginAt": "ISO-8601 | null"
}
```

## Acceptance criteria

- auth route schema가 `username`을 요구한다.
- schema가 대소문자 구분 정책과 공백 금지 정책을 문서화한다.
- schema가 `4..20` 길이 제약을 반영한다.
- admin session login/logout/me 흐름이 기존 동작을 유지한다.
- auth route 테스트가 새 계약 기준으로 통과한다.
- OpenAPI에 노출되는 auth schema도 `username` 기준이다.
- legacy admin response field `email`이 남아 있지 않다.

## Out of scope

- DB column rename 자체
- client auth 모델/UI 변경
- 루트 `docs/server/api-spec.md` 갱신

## Verify

- `(cd server && pnpm test -- test/routes/auth.test.ts)`
- 필요 시 `(cd server && pnpm test)`
