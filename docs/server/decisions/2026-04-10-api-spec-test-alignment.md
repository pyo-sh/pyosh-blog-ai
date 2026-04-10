# Decision 002: API Spec and Test Alignment Baseline

**날짜**: 2026-04-10
**상태**: accepted
**태그**: #api-spec #testing #contracts #documentation

## 배경

[`docs/server/api-spec.md`](/workspace/docs/server/api-spec.md)는 현재 `server/src` 라우트/스키마/테스트 구현을 기준으로 작성되었다고 선언하고 있다. 하지만 실제 구현과 테스트 구성을 대조해 보면, 스펙에 기재된 외부 계약 API 중 일부는 직접적인 route test가 없고, 문서 자체에도 최근 구현과 어긋난 설명이 남아 있다.

특히 다음 두 문제가 섞여 있다.

- 외부에 노출되는 API인데 route-level contract test가 없는 항목
- 이미 구현이 바뀌었는데 `api-spec.md`에 남아 있는 오래된 설명 또는 메타성 서술

이 상태에서는 "서버가 모든 API와 로직을 테스트로 확인하고 있다"라고 말할 수 없다.

## 검토 결과 요약

현재 route test가 존재하는 영역:

- Health
- Auth의 일부 (`admin/login`, `me`, `admin/logout`)
- Categories
- Assets
- Posts
- Tags
- Comments의 대부분
- Guestbook의 일부
- Stats
- User
- SEO

하지만 `api-spec.md` 기준으로는 아래 공백이 남아 있다.

### 1. route-level test가 빠진 API

- `GET /api/auth/csrf-token`
- `GET /api/auth/google`
- `GET /api/auth/google/callback`
- `GET /api/auth/github`
- `GET /api/auth/github/callback`
- `POST /api/comments/:id/reveal`
- `GET /api/settings/guestbook`
- `PATCH /api/admin/settings/guestbook`
- `DELETE /api/admin/guestbook/bulk`
- `PATCH /api/admin/guestbook/bulk`
- `PATCH /api/admin/guestbook/:id`

위 항목들은 실제 라우트 구현이 존재하지만, 현재 `test/routes/*.test.ts`에서는 직접 검증되지 않는다.

### 2. service test만 있고 공개 API contract test가 없는 영역

- Settings는 [`settings.route.ts`](/workspace/server/src/routes/settings/settings.route.ts)로 공개/관리자 API를 제공하지만, 현재는 [`settings.service.test.ts`](/workspace/server/test/services/settings.service.test.ts)만 있고 route test가 없다.

공개 계약은 service test만으로 대체하지 않는다. 인증, CSRF, 응답 형식, status code는 route test에서 검증해야 한다.

### 3. 이미 stale해진 `api-spec.md` 내용

- Auth 요청/응답 예시가 여전히 `email` 필드를 사용한다. 실제 구현은 `username`을 사용한다.
  - 근거: [`api-spec.md:140`](/workspace/docs/server/api-spec.md#L140), [`auth.route.ts:24`](/workspace/server/src/routes/auth/auth.route.ts#L24)
- `GET /api/auth/me`의 admin 응답 예시도 `email` 기준으로 적혀 있다. 실제 구현은 `username`을 반환한다.
  - 근거: [`api-spec.md:179`](/workspace/docs/server/api-spec.md#L179), [`auth.route.ts:200`](/workspace/server/src/routes/auth/auth.route.ts#L200)
- `## 현재 문서에서 바로잡은 점` 섹션은 스펙 본문이 아니라 과거 정정 이력을 섞어 놓은 메타 섹션이라 다시 stale해지기 쉽다.
  - 특히 `관리자 로그인 필드는 username이 아니라 email`이라는 문장은 현재 구현과 정반대다.
  - 근거: [`api-spec.md:1458`](/workspace/docs/server/api-spec.md#L1458), [`auth.route.ts:26`](/workspace/server/src/routes/auth/auth.route.ts#L26)
- `GET /api/health/ready`는 표에 존재하지만 응답 예시가 본문에 비어 있다.
  - 근거: [`api-spec.md:97`](/workspace/docs/server/api-spec.md#L97)

## 결정

서버 문서와 테스트는 다음 원칙으로 정렬한다.

### 1. `api-spec.md`에 실린 외부 계약 API는 route-level test를 기본 단위로 가진다

공개 경로, 관리자 경로, 조건부 등록 OAuth 경로를 포함해, 문서에 올린 API는 최소한 다음을 route test에서 검증해야 한다.

- 라우트 등록 여부
- 인증/권한 실패 코드
- CSRF 요구 여부
- 주요 성공 응답 형식
- 핵심 예외 분기

service test는 내부 로직 보강 용도로 유지하되, 외부 계약 검증을 대신하지 않는다.

### 2. `api-spec.md`는 역사 서술이 아니라 현재 계약만 남긴다

API 스펙 문서에는 다음만 남긴다.

- 현재 존재하는 엔드포인트
- 현재 요청/응답 계약
- 현재 동작 제약

반대로 아래는 제거하거나 별도 문서로 이동한다.

- 과거에 무엇을 바로잡았는지 설명하는 changelog성 문장
- 이미 구현과 충돌하는 예시
- 테스트나 구현 상태를 설명하는 임시 메모

### 3. 테스트가 red 상태이면 "검증 완료"로 간주하지 않는다

API 목록이 많더라도 테스트 스위트가 깨진 상태라면 coverage 존재만으로 충분하지 않다. route test 추가와 함께 기존 실패 테스트도 green 상태로 회복되어야 한다.

## 후속 작업

### 테스트 추가

- [ ] `GET /api/auth/csrf-token` route test 추가
- [ ] OAuth env 조건부 등록 경로(`google`, `google/callback`, `github`, `github/callback`)의 등록/미등록 behavior test 추가
- [ ] `POST /api/comments/:id/reveal` route test 추가
- [ ] `GET /api/settings/guestbook` route test 추가
- [ ] `PATCH /api/admin/settings/guestbook` route test 추가
- [ ] `DELETE /api/admin/guestbook/bulk` route test 추가
- [ ] `PATCH /api/admin/guestbook/bulk` route test 추가
- [ ] `PATCH /api/admin/guestbook/:id` route test 추가

### 검증 상태 회복

- [ ] 현재 red 상태인 테스트를 정리해 전체 서버 테스트 스위트를 green으로 복구

## 비고

이번 검토는 `api-spec.md`, `server/src/routes`, `server/test` 기준으로 수행했다. 결론은 "대부분의 핵심 API는 테스트가 있지만, 모든 API와 로직을 다 확인하고 있다고 보기는 어렵다"이다.
