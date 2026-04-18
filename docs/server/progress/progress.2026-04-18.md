# Server Progress - 2026-04-18

## Issue #96 Server API `/api` prefix 제거

- PR: #97
- 변경 범위:
  - `src/app.ts`에서 공개/관리자/API 인증 route prefix를 `/api/...`에서 루트 경로로 정리
  - OAuth callback URL을 `/auth/google/callback`, `/auth/github/callback`으로 전환
  - `src/routes/**` Swagger 설명과 주석 문자열을 새 경로 계약으로 갱신
  - `test/helpers/app.ts`, `test/routes/**` 통합 테스트 요청 경로를 새 계약으로 갱신
  - `api-spec.md`를 구현과 동일한 루트 경로 기준으로 갱신
- 리뷰 반영:
  - 초기 변경에서 `/health`가 DB 의존 상태 체크로 바뀌는 회귀가 지적됨
  - lightweight probe는 `GET /health`로 유지하고, 상세 상태 응답은 `GET /health/status`로 분리
- 검증:
  - `pnpm build`
  - `pnpm test` → `17` files, `266` tests passed

