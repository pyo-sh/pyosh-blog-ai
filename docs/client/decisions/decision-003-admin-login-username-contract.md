# Decision 003: Align client admin auth models to username contract

## Metadata
- **Date**: 2026-04-06
- **Status**: draft
- **Type**: feature
- **Area**: client

## Goal

Client admin login과 current-user 타입을 `username` 기준 계약으로 전환한다.

## Context

이 작업은 server auth contract 변경 이후에 수행해야 한다. 현재 클라이언트는 `username`을 입력받으면서도 API 타입과 응답 처리가 서로 맞지 않아 구조적으로 혼란스럽다.

이 문서는 client repo 내부 구현만 다룬다. 루트 `docs/server/api-spec.md` 갱신은 별도 docs 작업으로 처리한다.

## Issue Draft
- **Type**: feature
- **Area**: client
- **Goal**: Admin auth client 모델과 요청/응답 처리를 `username` 기준으로 정리한다.
- **Dependencies**:
  - `docs/server/decisions/decision-002-admin-auth-route-username-contract.md`
- **Priority**: priority:1

## Template mapping

- `feature.yml`
- `area`: `client`
- `goal`: Admin auth client 모델과 UI를 `username` 계약으로 전환
- `context`: server auth contract 변경 이후 legacy `email` 의미 제거 필요
- `requirements`: 아래 Requirements 섹션 사용
- `scope`: 아래 Scope 섹션 사용
- `dependencies`: server auth contract issue 생성 후 번호 치환
- `priority`: `priority:1`

## Scope

- Modify: `client/src/entities/auth/model.ts`
- Modify: `client/src/entities/auth/api.ts`
- Modify: `client/src/features/admin-login/ui/login-form.tsx`
- Review: `client/src/widgets/admin-sidebar/ui/admin-sidebar.tsx`
- Review: `client/src/app/(public)/guestbook/page.tsx`
- Review: `client/src/app/(public)/posts/[slug]/page.tsx`

## Requirements

- login request payload는 `{ username, password }`
- `username` 입력값은 대소문자를 구분하는 식별자임을 전제로 다룬다
- `username` 입력값은 `4..20` 길이 규칙을 따른다
- `username` 입력값에 앞뒤 공백을 `trim`하지 않는다
- 공백이 포함된 입력을 클라이언트에서 임의 보정하지 않는다
- 이메일 형식 힌트, `@` 전제, email autocomplete 기대를 제거한다
- login response unwrap이 서버 응답 구조와 일치해야 한다
- admin current-user 타입도 `username` 필드를 사용해야 한다
- admin auth 모델에 남아 있는 legacy `email`/`displayName`/잘못된 shape를 제거한다
- 로그인 입력 라벨/placeholder/helper text에서 admin identifier를 `email`로 오해할 여지를 제거한다
- 이메일 전용 validation이나 copy를 추가하지 않는다

## Target client contracts

### login request

```json
{
  "username": "관리자-01",
  "password": "password1234"
}
```

### login helper expected response from server

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

### `CurrentUser` admin shape

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

- 로그인 폼, auth model, auth api가 모두 같은 계약을 사용한다.
- admin user 타입이 server `/api/auth/me` 응답과 일치한다.
- admin 여부를 판별하는 기존 SSR/CSR 흐름은 유지된다.
- client auth domain에 admin identifier 의미의 `email` 필드가 남아 있지 않다.
- 로그인 UI와 helper가 입력값을 자동 보정하지 않는다.

## Verify

- `(cd client && pnpm compile:types && pnpm lint && pnpm build)`
