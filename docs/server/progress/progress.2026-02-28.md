# Progress: 2026-02-28

## Completed

- [x] Issue #10: 로깅 체계화 — PR #22 리뷰 반영 + 머지 완료
  - 리뷰 라운드 2회 진행 후 squash merge
  - **Round 1 리뷰 반영** (d8f0f47):
    - test 로그 레벨 `silent` → `warn` (테스트 중 경고/오류 진단 가능)
    - 5xx 중복 에러 로그 제거 (onSend → app.ts 에러 핸들러 단일화)
    - `app.close().then()` → `.finally()` (close 실패 시에도 process.exit 보장)
  - **Round 2 리뷰 반영** (4fd7f53):
    - `request.url` → `request.routeOptions.url` (쿼리스트링 민감정보 노출 방지)
    - `unhandledRejection` 로그 키 `{ reason }` → `{ err: reason }` (pino Error 직렬화 일관성)

## Notes

- 관련 PR: [PR #22](https://github.com/pyo-sh/pyosh-blog-be/pull/22)
- 초기 구현: [progress.2026-02-27.md](./progress.2026-02-27.md)
