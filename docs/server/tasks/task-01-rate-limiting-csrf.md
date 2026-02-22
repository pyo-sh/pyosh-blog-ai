# Task 01: Rate Limiting & CSRF 보호

> API 남용 방지를 위한 Rate Limiting + 세션 기반 CSRF 보호 적용

## 선행 조건

- [x] Fastify 전환 완료
- [x] 세션 기반 인증 구현 완료

## 작업 항목

### 1. Rate Limiting

- [x] **@fastify/rate-limit 플러그인 도입**
  - 글로벌 기본 설정 (100 req/min)
  - 테스트 환경에서는 비활성화 (반복 인증 패턴 허용)
- [x] **엔드포인트별 Rate Limit 세분화**
  - `POST /api/auth/admin/login`: 5 req/min (브루트포스 방지)
  - `POST /api/posts/:postId/comments`: 10 req/min (댓글 스팸 방지)
  - `POST /api/guestbook`: 10 req/min (방명록 스팸 방지)
  - `POST /api/stats/view`: 30 req/min (조회수 어뷰징 방지)
- [x] **Rate Limit 응답 표준화**
  - 429 응답에 `Retry-After` + `X-RateLimit-*` 헤더 포함

### 2. CSRF 보호

- [x] **CSRF 토큰 전략 결정**
  - Synchronizer Token Pattern (세션 기반) 채택 (findings 013 참고)
- [x] **@fastify/csrf-protection 도입**
  - 세션 기반 CSRF 토큰 생성/검증
  - 테스트 환경에서는 no-op 처리
- [x] **클라이언트 연동**
  - `GET /api/auth/csrf-token` 발급 엔드포인트 추가
  - state-changing 요청에 `onRequest: fastify.csrfProtection` 적용
    - `POST /api/auth/admin/logout`
    - `POST /api/posts/:postId/comments`, `DELETE /api/comments/:id`
    - `POST /api/guestbook`, `DELETE /api/guestbook/:id`
    - `POST /api/stats/view`

## 검증

- [x] Rate limit 초과 시 429 응답 확인 (프로덕션 환경)
- [x] CSRF 토큰 없는 POST 요청 거부 확인 (프로덕션 환경)
- [x] 정상 요청은 통과 확인
- [x] 기존 테스트 통과 (60/60)
