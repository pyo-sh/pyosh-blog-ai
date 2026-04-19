# Server Progress - 2026-04-10

## Issue #87 API spec and test alignment baseline

- PR: #90
- 상태: 머지 완료

### 변경 사항

- `auth`, `guestbook`, `settings` 라우트 테스트를 현재 API 계약에 맞게 정렬하고, 상태 변경 요청에 필요한 CSRF 헤더/쿠키 처리 헬퍼를 정리했다.
- `GET /api/auth/csrf-token` 경로와 실제 앱 라우팅을 대상으로 한 CSRF 통합 검증을 추가해 세션 기반 토큰 흐름을 end-to-end로 고정했다.
- `health`, `stats`, `settings.service` 테스트의 앱/DB lifecycle과 SQL assertion 방식을 보강해 공유 pool 종료 및 최근 조회 dedupe로 인한 불안정성을 제거했다.
- 누락돼 있던 guestbook 관리자 수정/벌크 경로와 guestbook 설정 조회·수정 커버리지를 추가해 red 상태였던 기준 테스트 스위트를 다시 green으로 복구했다.

### 검증

- `pnpm test`
  - `17`개 파일, `258`개 테스트 통과

## Issue #88 Dev uploads 상대 경로 계약 유지 및 정적 서빙 검증

- PR: #89
- 상태: 머지 완료

### 변경 사항

- 업로드 저장 루트와 `/uploads/` URL prefix 해석을 `src/shared/uploads.ts`로 공통화했다.
- static 플러그인이 서버 시작 시 업로드 디렉토리를 먼저 생성하도록 보강해 dev 환경에서 정적 루트 부재 경고를 제거했다.
- 파일 저장 `storageKey`를 POSIX 경로로 고정해 `/uploads/...` 상대 경로 계약을 일관되게 유지했다.
- assets 통합 테스트에 업로드 후 실제 저장 파일 존재와 `/uploads/...` 정적 접근 성공 검증을 추가했다.

### 검증

- `pnpm compile:types`
- `NODE_ENV=test ./node_modules/.bin/vitest run --pool forks --poolOptions.forks.singleFork test/routes/assets.test.ts`
- `pnpm test` 실행
  - 자산 테스트 24건은 통과
  - 전체 스위트는 기존 실패(`guestbook`, `stats`, `health`, `settings.service`)로 실패
