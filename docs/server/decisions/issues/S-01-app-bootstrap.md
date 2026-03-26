# App bootstrap + health check

> Fastify 5 앱 초기화, 플러그인 등록, 전역 에러 핸들러, health check 4개 엔드포인트 구현

## SPEC 참조

- `docs/server/api-spec.md` > Health check, 에러 응답 형식
- `docs/architecture.md` > 기술 스택 (Server)

## 상세

### Fastify 5 초기화

Fastify 5 인스턴스를 생성하고 다음 플러그인을 등록한다:

| 플러그인 | 용도 |
|---|---|
| `@fastify/cors` | CORS 설정 |
| `@fastify/helmet` | 보안 헤더 |
| `@fastify/session` | 세션 관리 |
| `@fastify/cookie` | 쿠키 파싱 |
| `@fastify/multipart` | 파일 업로드 |
| `@fastify/rate-limit` | Rate limiting |
| `@fastify/csrf-protection` | CSRF 보호 |
| `fastify-type-provider-zod` | Zod 스키마 검증 |

기술 스택 참조:

| 영역 | 기술 | 비고 |
|---|---|---|
| 프레임워크 | Fastify 5 | |
| 언어 | TypeScript 5.9 | |
| DB | MySQL | mysql2 드라이버 |
| ORM | Drizzle ORM | + Drizzle Kit (마이그레이션) |
| 검증 | Zod | fastify-type-provider-zod |
| 인증 | Passport (Google, GitHub OAuth) | + argon2 (관리자 비밀번호) |
| 세션 | @fastify/session + cookie | |
| 보안 | helmet, CSRF, rate-limit, CORS | |
| 파일 업로드 | @fastify/multipart | 로컬 파일시스템 저장 |
| API 문서 | Swagger + Swagger UI | |
| 테스트 | Vitest | |

### 전역 에러 핸들러

모든 에러 응답은 다음 형식을 따른다:

```json
{ "statusCode": 400, "error": "Bad Request", "message": "..." }
```

에러 핸들러 동작:
1. HttpError - 해당 statusCode + message 반환
2. Fastify validation error - 400 + 검증 에러 상세
3. 그 외 - 500 + 로그 기록 (스택 트레이스, 요청 정보)

프로덕션에서 500 에러 메시지를 클라이언트에 노출하지 않는다 ("An unexpected error occurred").

### Health check 엔드포인트

| Method | Path | 설명 |
|---|---|---|
| GET | `/health` | `{ "status": "ok", "timestamp": "ISO" }` |
| GET | `/api/health` | 전체 헬스체크 (DB 포함) |
| GET | `/api/health/live` | Liveness probe (DB 미확인) |
| GET | `/api/health/ready` | Readiness probe (DB 확인, 실패 시 non-200) |

#### GET `/api/health/live`

**Response 200:**
```json
{ "status": "ok", "timestamp": "ISO", "uptime": 12345, "version": "string" }
```

#### GET `/api/health/ready`

**Response 200:**
```json
{
  "status": "ok", "timestamp": "ISO", "uptime": 12345, "version": "string",
  "memory": { "rss": 0, "heapUsed": 0, "heapTotal": 0 },
  "database": { "status": "ok", "latencyMs": 5 }
}
```

DB 연결 실패 시 503 응답을 반환한다.

### Rate limiting 전역 설정

| 엔드포인트 | 제한 |
|---|---|
| `POST /api/auth/admin/login` | 5 req/min |
| `POST /api/posts/:postId/comments` | 10 req/min |
| `POST /api/guestbook` | 10 req/min |
| `POST /api/stats/view` | 30 req/min |

## 수용 기준

- [ ] Fastify 5 인스턴스가 생성되고 모든 플러그인이 정상 등록된다
- [ ] cors, helmet, session, cookie, multipart, rate-limit, csrf-protection 플러그인이 등록된다
- [ ] 전역 에러 핸들러가 HttpError, validation error, 미처리 에러를 분류하여 응답한다
- [ ] 에러 응답 형식이 `{ statusCode, error, message }` 구조를 따른다
- [ ] 프로덕션에서 500 에러 시 내부 메시지가 노출되지 않는다
- [ ] `GET /health`가 `{ status: "ok", timestamp }` 를 반환한다
- [ ] `GET /api/health`가 DB 포함 전체 헬스체크를 수행한다
- [ ] `GET /api/health/live`가 version, uptime 포함 응답을 반환한다
- [ ] `GET /api/health/ready`가 DB 연결 확인 후 정상 시 200, 실패 시 503을 반환한다
- [ ] Rate limiting 전역 설정이 등록된다

## 의존성

- Blocked by: 없음
- Blocks: S-03, S-04~S-12

## 참고

- `GET /health`는 로드밸런서 기본 헬스 체크용으로 가장 가볍게 유지한다.
- `GET /api/health/ready`는 readiness probe로 사용하며, DB 연결 실패 시 non-200을 반환하여 트래픽 라우팅을 차단한다.
- `APP_VERSION`은 `npm_package_version` 폴백으로 사용한다.
