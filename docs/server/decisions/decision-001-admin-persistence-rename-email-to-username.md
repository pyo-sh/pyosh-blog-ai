# Decision 001: Rename admin persistence from email to username

## Metadata
- **Date**: 2026-04-06
- **Status**: draft
- **Type**: refactor
- **Area**: server

## Problem

Admin 로컬 인증의 실제 식별자는 `username`이어야 하지만, 현재 persistence와 service 레이어가 `email`로 고정되어 있다. 이 상태는 auth route뿐 아니라 DB schema, seed, 테스트 fixture 전반에 legacy 용어를 퍼뜨린다.

## Improvement

- `admin_tb.email`을 `username`으로 직접 rename한다.
- service와 fixture도 동일한 용어를 사용한다.
- route 계약 변경 전, persistence/domain layer부터 정리해서 이후 route/client 변경이 자연스럽게 따라오게 만든다.

## Source-of-truth policy

- Admin 로컬 인증의 식별자는 `username` 단일 값이다.
- `email`은 Admin 도메인에서 compatibility alias로 유지하지 않는다.
- DB 레벨에서도 `admin_tb.email`을 `admin_tb.username`으로 직접 rename한다.
- legacy `email` 의미를 암시하는 검증, 변수명, 메시지, fixture, 문서 예시는 모두 제거 대상이다.

## Issue Draft
- **Type**: refactor
- **Area**: server
- **Problem**: Admin 인증 persistence가 `email` 용어를 사용해 실제 도메인과 어긋난다.
- **Improvement**: Admin DB schema, service lookup, seed fixture를 `username` 기준으로 재정렬한다.
- **Dependencies**: 없음
- **Priority**: priority:1

## Template mapping

- `refactor.yml`
- `area`: `server`
- `problem`: Admin 식별자 legacy naming이 persistence와 service에 남아 있음
- `improvement`: DB schema와 service naming을 `username`으로 통일
- `scope`: 아래 Scope 섹션 사용
- `dependencies`: `없음`
- `priority`: `priority:1`

## Fixed implementation rules

- `admin_tb.email`을 유지하지 않는다.
- `username` 신규 컬럼 추가 후 dual-field 기간을 두지 않는다.
- migration은 rename 기준으로 작성한다.
- 기존 admin row는 기존 `email` 값을 그대로 `username` 값으로 보존한다.
- service/API code에 compatibility alias (`email ?? username`)를 두지 않는다.
- Admin 도메인에서 식별자 의미의 `email` 변수명, 타입명, fixture명을 남기지 않는다.

## Username rules to enforce in this layer

- 최소 길이: `4`
- 최대 길이: `20`
- 허용 문자: 모든 언어 문자, 숫자, `_`, `-`, `.`
- 허용 정규식 기준: `^[\p{L}\p{N}_.-]{4,}$` with Unicode mode
- 대소문자를 구분한다.
- 앞뒤 공백도 허용하지 않는다.
- 내부 공백도 허용하지 않는다.
- 입력값을 `trim`하여 보정하지 않는다.
- 이메일 포맷 검증은 하지 않는다.

## DB implementation rule

- `username` column은 대소문자 구분 unique 비교가 되도록 정의한다.
- 권장 기준은 MySQL `utf8mb4_bin` 계열의 case-sensitive collation/definition이다.
- `Admin`과 `admin`은 서로 다른 username으로 저장 가능해야 한다.

## Legacy removal checklist

- DB column name
- Drizzle schema field name
- service method parameter names
- test fixture names and seeded values
- auth failure messages used in server layer
- comments and docs in server repo that still treat admin identifier as email

## Scope

- Modify: `server/src/db/schema/admins.ts`
- Modify: `server/src/routes/auth/admin.service.ts`
- Modify: `server/test/helpers/seed.ts`
- Modify: `server/test/routes/auth.test.ts`
- Modify if referenced: `server/scripts/hash-password.ts`
- Review: `server/src/hooks/auth.hook.ts`
- Add: `server/drizzle/*.sql` username migration
- Update if needed: `server/drizzle/meta/*`

## Acceptance criteria

- Admin schema가 `username` 필드를 사용한다.
- `username` column 길이 제한이 `4..20` 규칙과 충돌하지 않는다.
- migration 이후 DB에는 login identifier 의미의 `email` 컬럼이 남지 않는다.
- Admin 조회 로직이 `username`으로 동작한다.
- DB uniqueness가 대소문자 구분 정책과 충돌하지 않도록 정의된다.
- 테스트 seed와 auth fixture가 `username` 기준으로 읽힌다.
- 더 이상 admin persistence/service 코드에 `email`이 식별자 의미로 남지 않는다.
- rename 이후에도 기존 seeded admin 계정은 로그인 가능하다.

## Out of scope

- route body schema와 API response field 변경
- client auth 타입 및 UI 변경

## Verify

- `(cd server && pnpm test -- test/routes/auth.test.ts)`
- 필요 시 `(cd server && pnpm test)`
