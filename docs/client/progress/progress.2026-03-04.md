# Progress: 2026-03-04

## Completed

- [x] CSRF 토큰 유틸리티 구현 - `getCsrfToken()` (캐싱 + lazy fetch), `clearCsrfToken()` (#34)
- [x] mutation helper 구현 - `clientMutate<T>()` (CSRF 토큰 자동 주입) (#34)
- [x] barrel export 업데이트 - `src/shared/api/index.ts` (#34)
- [x] DoD 검증 - `pnpm compile:types && pnpm lint && pnpm build` 통과 (#34)

- [x] Auth entity 타입 정의 - `AdminUser`, `LoginCredentials` (#38)
- [x] Auth API 함수 구현 - `login`, `logout`, `fetchMe`, `fetchMeServer` (#38)
- [x] barrel export 생성 - `src/entities/auth/index.ts` (#38)
- [x] DoD 검증 - `pnpm compile:types && pnpm lint && pnpm build` 통과 (#38)

## Notes

- `getCsrfToken()`은 모듈 레벨 변수로 토큰 캐싱. 로그아웃 시 `clearCsrfToken()` 호출로 초기화.
- `clientMutate`는 `clientFetch` 래퍼로, mutation 메서드(POST/PUT/PATCH/DELETE) 호출 시 `x-csrf-token` 헤더 자동 주입.
- #38: `fetchMe`는 클라이언트 컴포넌트용 (`clientFetch`), `fetchMeServer`는 RSC용 (`serverFetch` + cookieHeader).
- #34 dependency는 아직 OPEN 상태이나, `clientFetch`/`serverFetch` 직접 사용으로 독립 구현.

## Review outcomes (#34, PR #119)

3라운드 리뷰 진행 후 merge:
- Round 1: promise caching 패턴 적용 (`cachedToken` → `tokenPromise`), `clientMutate` 기본 method POST 추가, CSRF 헤더 override 방지
- Round 2: rejected promise 영구 캐싱 버그 수정 - `.catch`에서 `tokenPromise = null` 재설정
- Round 3: APPROVED (suggestion만 - 403 auto-retry, Phase 2엔 급하지 않음으로 스킵)
