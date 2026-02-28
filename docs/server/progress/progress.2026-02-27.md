# Progress: 2026-02-27

## Completed

- [x] Issue #10: 로깅 체계화 — 구조화 로깅 구현
  - `src/plugins/logger.ts` 신규 생성: `buildLoggerOptions()` + `loggerPlugin`
    - 환경별 로그 레벨: development=debug, production=info, test=silent
    - pino redact: `Authorization`, `Cookie`, `Set-Cookie` 헤더 자동 마스킹
    - 개발 환경: pino-pretty (colorize, translateTime)
    - 프로덕션: JSON 포맷 (추가 설정 없음)
  - `src/app.ts` 업데이트:
    - `buildLoggerOptions()` 사용으로 로거 설정 중앙화
    - `loggerPlugin` 등록 (플러그인 체인 첫 번째)
    - 에러 핸들러 강화: `request.log.error({ err, method, url, ip, userId }, ...)` — 스택 트레이스 + 요청 컨텍스트
  - `src/server.ts` 업데이트:
    - `console.log` → `app.log.info/error` 전환
    - `uncaughtException` / `unhandledRejection` 핸들러 추가 (graceful shutdown)

## Issues & Resolutions

- **Issue**: `error` 파라미터를 `{ message, stack, name }`로 분해 시 TypeScript strict 오류 (`TS2339: Property does not exist on type 'unknown'`)
- **Resolution**: pino의 `err` 직렬화키를 활용하여 `{ err: error }` 그대로 전달 — pino가 Error 객체를 자동 직렬화

## Next Steps

- [x] PR 리뷰 후 머지 → [progress.2026-02-28.md](./progress.2026-02-28.md)
