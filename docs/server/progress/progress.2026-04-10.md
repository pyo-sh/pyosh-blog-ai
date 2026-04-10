# Server Progress - 2026-04-10

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
