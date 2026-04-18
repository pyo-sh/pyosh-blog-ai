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

## Issue #98 Server PR/push CI 추가

- PR: #99
- 변경 범위:
  - `server/.github/workflows/ci.yml` 신규 추가
  - `pull_request`와 `main` 대상 `push`에서 Node 20 + pnpm 기반 CI 실행
  - MySQL service와 `.env.test` 생성 step을 포함해 `pnpm compile:types`, `pnpm lint`, `pnpm test`, `pnpm build`를 PR 단계 검증으로 연결
  - 리뷰 반영으로 open PR 중복 실행을 막기 위해 `push` 범위를 `main`으로 제한하고, pnpm 버전을 `10.33.0`으로 고정
- 검증:
  - `pnpm compile:types`
  - `pnpm build`
  - `pnpm lint` → 기존 베이스라인 lint 오류로 실패
  - `pnpm test` → 로컬 DB 권한 부족으로 실패, CI에서는 workflow 내 MySQL service로 실행 예정
