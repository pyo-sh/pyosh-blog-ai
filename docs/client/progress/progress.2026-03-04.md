# Progress: 2026-03-04

## Completed

- [x] CSRF 토큰 유틸리티 구현 - `getCsrfToken()` (캐싱 + lazy fetch), `clearCsrfToken()` (#34)
- [x] mutation helper 구현 - `clientMutate<T>()` (CSRF 토큰 자동 주입) (#34)
- [x] barrel export 업데이트 - `src/shared/api/index.ts` (#34)
- [x] DoD 검증 - `pnpm compile:types && pnpm lint && pnpm build` 통과 (#34)

## Notes

- `getCsrfToken()`은 모듈 레벨 변수로 토큰 캐싱. 로그아웃 시 `clearCsrfToken()` 호출로 초기화.
- `clientMutate`는 `clientFetch` 래퍼로, mutation 메서드(POST/PUT/PATCH/DELETE) 호출 시 `x-csrf-token` 헤더 자동 주입.
- Phase 2 admin 기능의 prerequisite 완료.
