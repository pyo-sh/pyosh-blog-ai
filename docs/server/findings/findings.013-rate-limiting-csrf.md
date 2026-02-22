# Findings 013: Rate Limiting & CSRF 보호 전략

**날짜**: 2026-02-22
**태그**: #rate-limit #csrf #security #fastify

## 📝 요약

`@fastify/rate-limit` (글로벌 + 엔드포인트별)과 `@fastify/csrf-protection` (Synchronizer Token)을 도입하여 API 남용 및 CSRF 공격을 방어.

## 🎯 목표

- 브루트포스 / 스팸 요청 방어
- 세션 기반 인증 환경에서 CSRF 공격 차단

## 🔧 기술 선택

### Rate Limiting: @fastify/rate-limit v10.3.0

- **Fastify 5 호환**: v10.x → Fastify 5.x 지원
- **글로벌 기본값**: 100 req/min (전체 API)
- **엔드포인트별 오버라이드**: `config.rateLimit` 라우트 옵션으로 세분화
- **429 응답 헤더**: `Retry-After` + `X-RateLimit-{Limit,Remaining,Reset}` 자동 포함

| 엔드포인트 | 제한 | 이유 |
|-----------|------|------|
| `POST /api/auth/admin/login` | 5/min | 브루트포스 방지 |
| `POST /api/posts/:postId/comments` | 10/min | 댓글 스팸 방지 |
| `POST /api/guestbook` | 10/min | 방명록 스팸 방지 |
| `POST /api/stats/view` | 30/min | 조회수 어뷰징 방지 |

### CSRF 전략: Synchronizer Token Pattern vs Double Submit Cookie

| 기준 | Synchronizer Token | Double Submit Cookie |
|------|-------------------|----------------------|
| 보안 강도 | ✅ 높음 (서버 검증) | ⚠️ 중간 (쿠키 접근 가능한 XSS에 취약) |
| 세션 의존 | ✅ 기존 세션과 통합 | ❌ 별도 쿠키 필요 |
| Stateless | ❌ (서버 상태 필요) | ✅ |
| **선택** | ✅ **채택** | ❌ |

**채택 이유**: 이미 `@fastify/session` 기반의 세션 인프라가 있어 자연스럽게 통합 가능.

### CSRF 플러그인: @fastify/csrf-protection v7.1.0

- `sessionPlugin: '@fastify/session'` 으로 세션에 시크릿 저장
- `reply.generateCsrf()` → 토큰 발급 (동기)
- `fastify.csrfProtection` → `onRequest` 훅으로 토큰 검증
- 토큰 전달: `x-csrf-token` 헤더 (기본값)

## 🏗️ 구현 패턴

```typescript
// 플러그인 등록 순서 (app.ts)
// helmet → rate-limit → drizzle → session → csrf → passport → ...

// CSRF 토큰 발급
GET /api/auth/csrf-token
→ { token: string }

// 보호된 엔드포인트
fastify.post('/guestbook', {
  config: { rateLimit: { max: 10, timeWindow: '1 minute' } },
  onRequest: fastify.csrfProtection,
  ...
})
```

## 🐛 이슈 & 해결

### 테스트 환경에서 Rate Limit 충돌
- **문제**: admin login 5/min 제한으로 다수 테스트 케이스가 동일 앱 인스턴스에서 실패
- **해결**: `NODE_ENV === 'test'` 시 rate-limit 플러그인 no-op 처리

### 테스트 환경에서 CSRF 처리
- **문제**: 기존 테스트는 CSRF 토큰 없이 POST/DELETE 호출
- **해결**: `NODE_ENV === 'test'` 시 `csrfProtection` no-op, `generateCsrf` mock으로 등록

## 🎓 교훈

1. **테스트 격리**: 보안 플러그인은 테스트 환경 분기가 필수
2. **onRequest vs preHandler**: CSRF는 헤더 기반이면 `onRequest`가 적합 (body 파싱 전 실행)
3. **플러그인 등록 순서**: `rate-limit`은 helmet 직후, `csrf`는 session 의존성으로 세션 이후

## 📚 참고 자료

- [@fastify/rate-limit README](https://github.com/fastify/fastify-rate-limit)
- [@fastify/csrf-protection README](https://github.com/fastify/csrf-protection)
- [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
