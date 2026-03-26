# Server Progress Index

> Server(Fastify) 진행 상황 요약

## 📅 타임라인

| 날짜       | 주요 작업                              | 상태 |
| ---------- | -------------------------------------- | ---- |
| 2026-03-26 | Issue #36 Tags API: GET /api/tags already implemented on main; added empty-state test + PR #55 머지 | ✅   |
| 2026-03-26 | Issue #37 Posts public API: GET /api/posts/slugs, PostListItem/PostDetail schemas (totalPageviews, commentCount, ancestors), filter param, batch enrichment + PR #54 머지 | ✅   |
| 2026-03-26 | Issue #35 Guestbook + settings API: 8 guestbook endpoints + 2 settings endpoints, DELETE/PATCH HTTP semantics split, status-guard filters, soft_delete idempotency + PR #53 머지 | ✅   |
| 2026-03-26 | Issue #32 Logging and error management: prod multistream(stdout+error.log), req body 마스킹, test disableRequestLogging, discriminated union 타입 + PR #50 머지 | ✅   |
| 2026-03-26 | Issue #31 Auth system: OAuth 전략/라우트 env 조건부 등록, `optionalAuth` null 명시, `user` 타입 확장 + PR #51 머지 | ✅   |
| 2026-03-26 | Issue #29 DB schema + migrations: `post_tb` 5개 컬럼 추가(summary, description, commentStatus, isPinned, contentModifiedAt) + migration 0004 + PR #49 머지 | ✅   |
| 2026-03-26 | Issue #28 Env Zod validation: `Object.freeze()` 추가, `constants/env.ts` 삭제, `.env.example` 갱신 + PR #48 머지 | ✅   |
| 2026-03-26 | Issue #30 App bootstrap + health check: `GET /api/health` memory 필드 누락 수정 + PR #47 머지 | ✅   |
| 2026-02-28 | Issue #10 로깅 체계화: PR #22 리뷰 2라운드 반영 + squash merge (routeOptions.url 보안, pino err 키 일관성) | ✅   |
| 2026-02-27 | Issue #10 로깅 체계화: buildLoggerOptions(env 레벨/redact), loggerPlugin, 에러 핸들러 컨텍스트 강화, uncaughtException/unhandledRejection 처리 | ✅   |
| 2026-02-25 | Issue #15 GET /api/assets 에셋 목록 엔드포인트 추가 + dev-pipeline 스킬 CLI 옵션 수정 | ✅   |
| 2026-02-25 | Issue #13 GET /api/admin/posts 쿼리 파라미터 문서화 및 구현 (AdminPostListQuerySchema + api-spec) | ✅   |
| 2026-02-24 | PR #19 최종 반영: main 충돌 해소 + `/api/health` memory 응답 복원 + 머지 준비 완료 | ✅   |
| 2026-02-24 | PR #19 리뷰 3차 반영: env 로더 단일화 + migration 조건부 실행 + health 핸들러 중복 정리 | ✅   |
| 2026-02-24 | Issue #12 배포 인프라 강화: Health Check 확장 + DB 마이그레이션 스크립트/CI 워크플로 추가 + .env.example/테스트 보강 | ✅   |
| 2026-02-24 | Issue #16 Guestbook 스키마 문서화 + Issue #14 GET /api/tags(postCount) 복구 | ✅   |
| 2026-02-06 | 기술 스택 분석 & Phase 0 (Express 5)   | ✅   |
| 2026-02-09 | 마이그레이션 결정 & Phase S-0, S-1     | ✅   |
| 2026-02-10 | Phase S-2~S-6 (Fastify + Drizzle 완성), Phase 3 (Taxonomy), Phase 4 (Assets) | ✅   |
| 2026-02-16 | Task 01 Stats + Task 02 SEO(Sitemap/RSS) 구현 및 문서 로그 반영 | ✅   |
| 2026-02-19 | Task 03 테스트 인프라 설정 + Task 04 Auth Integration Test        | ✅   |
| 2026-02-20 | Task 06 Posts Integration Test (12 cases) + 서비스 버그 2건 수정  | ✅   |
| 2026-02-20 | Task 07 Comments & Guestbook Integration Test (16 cases) + 라우트 버그 3건 수정 | ✅   |
| 2026-02-20 | Task 08 이후 작업 범위 lint fix 완료 (0 errors, 0 warnings) | ✅   |
| 2026-02-22 | E1. 최초 관리자 계정 생성 기능 삭제 (setup 엔드포인트 제거 + hash-password 스크립트) | ✅   |
| 2026-02-22 | E6 (task-03). /api/user/me GET/PUT/DELETE 신규 구현 + 탈퇴 유저 마스킹 (58 tests) | ✅   |
| 2026-02-22 | E2 (task-04). Post thumbnailUrl 전환 + Drizzle backfill migration + Posts API/테스트 반영 | ✅   |
| 2026-02-22 | E4 (task-05). Tag API 제거 + Posts tagSlug 검색 전환 + 테스트/문서 반영 | ✅   |
| 2026-02-22 | E3 (task-06). GET /api/categories/:slug 제거 + Categories 트리 API 단일화 + 문서/테스트 갱신 | ✅   |
| 2026-02-22 | Task 01. Rate Limiting (글로벌 100/min + 엔드포인트별) + CSRF 보호 (Synchronizer Token) 구현 | ✅   |
| 2026-02-22 | Task 02. 게시글 검색 API (GET /api/posts?q=keyword) MySQL LIKE 방식 구현 + 테스트 3건 추가 | ✅   |
| 2026-02-22 | Task 03. 관리자 댓글/방명록 목록 API (GET /api/admin/comments, GET /api/admin/guestbook) + 테스트 8건 추가 | ✅   |

## 🔗 상세 문서

- [progress.2026-03-26.md](./progress/progress.2026-03-26.md) - Issue #35 Guestbook + settings API: 8 endpoints + settings service + PR #53 머지
- [progress.2026-03-26.md](./progress/progress.2026-03-26.md) - Issue #30 app bootstrap: /api/health memory 필드 추가 + PR #47 머지
- [progress.2026-02-28.md](./progress/progress.2026-02-28.md) - Issue #10 PR #22 리뷰 반영 + squash merge 완료
- [progress.2026-02-27.md](./progress/progress.2026-02-27.md) - Issue #10 로깅 체계화: pino logger 최적화 + 에러 컨텍스트 로깅 + uncaught 예외 처리
- [progress.2026-02-25.md](./progress/progress.2026-02-25.md) - Issue #13 GET /api/admin/posts 쿼리 파라미터 문서화 및 구현
- [progress.2026-02-24.md](./progress/progress.2026-02-24.md) - Issue #12 배포 인프라 강화(Health Check + Migration 자동화 + env 샘플/테스트)
- [progress.2026-02-24.md](./progress/progress.2026-02-24.md) - PR #19 리뷰 3차 반영(env 로더 단일화, migration 조건부 실행, health 중복 정리)
- [progress.2026-02-24.md](./progress/progress.2026-02-24.md) - PR #19 최종 반영(main 충돌 해결, /api/health memory 복원, merge blocker 해소)
- [progress.2026-02-24.md](./progress/progress.2026-02-24.md) - Issue #16 Guestbook API 스키마 문서화 + Issue #14 GET /api/tags 복구
- [progress.2026-02-06.md](./progress/progress.2026-02-06.md) - 기술 스택 분석 & Phase 0
- [progress.2026-02-09.md](./progress/progress.2026-02-09.md) - Fastify 전환 시작
- [progress.2026-02-10.md](./progress/progress.2026-02-10.md) - Fastify + Drizzle 완성, Taxonomy Modules, Assets Module
- [progress.2026-02-16.md](./progress/progress.2026-02-16.md) - Stats + SEO(Sitemap/RSS) 구현 및 task/findings 반영
- [progress.2026-02-19.md](./progress/progress.2026-02-19.md) - Task 03 테스트 인프라 설정
- [progress.2026-02-20.md](./progress/progress.2026-02-20.md) - Task 06/07 및 Task 08 이후 lint fix 작업
- [progress.2026-02-22.md](./progress/progress.2026-02-22.md) - E1 관리자 setup 제거, E6 /api/user 구현, E2 thumbnailUrl 전환, E4 Tag API 제거, E3 categories slug 제거

## 📊 최종 성과

### 기술 스택 전환

- **Express → Fastify** 완료
- **TypeORM → Drizzle ORM** 완료
- **class-validator → Zod** 완료
- **Mocha → Vitest** 완료

### 성능 & 번들

- **성능**: 2-3배 향상 (Fastify 벤치마크)
- **번들 크기**: 80% 감소 (Drizzle)
- **쿼리 성능**: 1.5-2배 향상

### 코드 품질

- **의존성**: 77개 → 43개 (44% 감소)
- **LOC**: ~2,464 → ~1,200 (51% 감소)
- **커스텀 프레임워크**: 500 LOC → 0 LOC (100% 제거)
- **experimentalDecorators**: 제거 (TC39 표준 준수)
