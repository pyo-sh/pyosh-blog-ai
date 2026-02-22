# Server Tasks - 실행 계획

> will.md 기반으로 정리한 작업 목록 (완료된 레거시 정리 항목 제외)

## 실행 순서 (의존성 기준)

```
Phase 1: 보안 강화
└── task-01. Rate Limiting & CSRF 보호       ← 독립, 우선 적용

Phase 2: 기능 확장 (병렬 가능)
├── task-02. 게시글 검색 API                 ← 독립
├── task-03. 관리자 댓글/방명록 관리 API     ← 독립
├── task-04. 게시글 시리즈/연재              ← 독립
└── task-05. 초안 자동 저장                  ← 독립

Phase 3: 미디어 & 성능
├── task-06. 이미지 최적화 & 에셋 정리       ← 독립
└── task-07. 캐싱 & 조회수 중복 제거 개선    ← 독립

Phase 4: 품질 & 인프라
├── task-08. 로깅 체계화                     ← 독립
├── task-09. 테스트 확대 & API 에러 표준화   ← Phase 1-3 이후 권장
└── task-10. 배포 인프라 강화                ← 독립
```

## 파일 목록

| 파일 | 설명 | 우선순위 | 상태 |
|------|------|----------|------|
| [task-01-rate-limiting-csrf.md](./task-01-rate-limiting-csrf.md) | Rate Limiting + CSRF 보호 | P0 | 대기 |
| [task-02-post-search-api.md](./task-02-post-search-api.md) | 게시글 검색 API | P1 | 대기 |
| [task-03-admin-comments-guestbook.md](./task-03-admin-comments-guestbook.md) | 관리자 댓글/방명록 관리 API | P1 | 대기 |
| [task-04-post-series.md](./task-04-post-series.md) | 게시글 시리즈/연재 기능 | P1 | 대기 |
| [task-05-draft-autosave.md](./task-05-draft-autosave.md) | 초안 자동 저장 | P2 | 대기 |
| [task-06-image-optimization.md](./task-06-image-optimization.md) | 이미지 최적화 & 에셋 정리 | P2 | 대기 |
| [task-07-caching-viewcount.md](./task-07-caching-viewcount.md) | 캐싱 전략 & 조회수 개선 | P2 | 대기 |
| [task-08-structured-logging.md](./task-08-structured-logging.md) | 구조화된 로깅 (pino) | P2 | 대기 |
| [task-09-test-error-standardization.md](./task-09-test-error-standardization.md) | 테스트 확대 & API 에러 표준화 | P1 | 대기 |
| [task-10-deploy-infra.md](./task-10-deploy-infra.md) | 환경변수 검증 + Health check + 마이그레이션 자동화 | P2 | 대기 |

## 완료된 작업 (이전 세션)

> will.md의 다음 항목은 이미 구현 완료되어 제외됨

- ~~User 라우트 인증 가드~~ → `/api/user/me` requireAuth 적용됨
- ~~OAuth → oauth_account_tb 마이그레이션~~ → 완료
- ~~user_tb / image_tb 정리~~ → DROP 완료 (0001 migration)
- ~~태그 삭제 API~~ → Tag API 전체 제거됨
