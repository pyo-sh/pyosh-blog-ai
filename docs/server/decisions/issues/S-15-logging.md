# Logging and error management

> Pino 로깅 설정 (dev/prod/test), 민감 데이터 마스킹, 에러 분류 체계, health check 문서화

## SPEC 참조

- `docs/specs/deploy-monitoring.md` > 5.1 서버 로깅 (Pino), 5.2 민감 데이터 마스킹, 5.3 에러 분류 체계, 5.5 헬스 체크 엔드포인트

## 상세

### 5.1 서버 로깅 (Pino)

#### 환경별 설정

| 설정 | Development | Production | Test |
|---|---|---|---|
| 로그 레벨 | `debug` | `info` | `warn` |
| 포맷 | `pino-pretty` (가독성) | JSON (기계 파싱) | JSON |
| 요청 로깅 | 전체 | 전체 | 비활성 |
| 출력 대상 | stdout만 | stdout + error.log 파일 | stdout만 |

#### 프로덕션 로그 출력 (stdout + 파일)

프로덕션에서 Pino `multistream`으로 stdout과 에러 로그 파일을 동시에 사용한다.

```typescript
import pino from 'pino';

const streams: pino.StreamEntry[] = [
  // 1. stdout: 모든 레벨 (info+)
  { level: 'info', stream: process.stdout },

  // 2. error.log: error 레벨만 파일에 기록
  { level: 'error', stream: pino.destination('logs/error.log') },
];

const logger = pino(
  { level: 'info' },
  pino.multistream(streams),
);
```

- **stdout**: 실시간 모니터링 (터미널, Docker logs)
- **logs/error.log**: 에러만 파일에 기록 (검색/분석용)
- `logs/` 디렉토리는 `.gitignore`에 추가
- 로그 파일 로테이션/보존은 인프라 레벨에서 관리 (logrotate 등)

#### 로그 레벨 사용 기준

| 레벨 | 용도 | 예시 |
|---|---|---|
| `error` | 서비스에 영향을 주는 에러 | 미처리 예외, DB 연결 실패, 파일 저장 실패 |
| `warn` | 주의가 필요하지만 서비스는 정상 | Rate limit 초과, 인증 실패, 잘못된 요청 |
| `info` | 운영 상태 확인 | 서버 시작, 요청/응답, 세션 생성/파괴 |
| `debug` | 개발 시 디버깅 | SQL 쿼리, 요청 본문, 내부 상태 |

#### 요청/응답 로그 포맷

```json
{
  "level": "info",
  "time": 1711234567890,
  "reqId": "req-1",
  "req": {
    "method": "POST",
    "url": "/api/admin/posts",
    "ip": "192.168.1.1"
  },
  "res": {
    "statusCode": 201
  },
  "responseTime": 45,
  "msg": "request completed"
}
```

#### 에러 로그 포맷

```json
{
  "level": "error",
  "time": 1711234567890,
  "reqId": "req-1",
  "err": {
    "type": "Error",
    "message": "Connection refused",
    "stack": "Error: Connection refused\n    at ..."
  },
  "req": {
    "method": "POST",
    "url": "/api/admin/posts",
    "ip": "192.168.1.1"
  },
  "userId": 1,
  "msg": "Unhandled server error"
}
```

### 5.2 민감 데이터 마스킹

#### 현재 마스킹 대상 (기존 구현)

| 필드 | 처리 |
|---|---|
| `req.headers.authorization` | `[REDACTED]` |
| `req.headers.cookie` | `[REDACTED]` |
| `req.headers['set-cookie']` | `[REDACTED]` |
| `res.headers['set-cookie']` | `[REDACTED]` |

#### 추가 마스킹 대상

| 필드 | 처리 | 이유 |
|---|---|---|
| 요청 body의 `password` | 로깅하지 않음 | 비밀번호 노출 방지 |
| 요청 body의 `guestPassword` | 로깅하지 않음 | 게스트 비밀번호 |
| 요청 body의 `guestEmail` | 로깅하지 않음 | 개인정보 |
| 에러 로그의 `userId` | 포함 | 디버깅에 필요 (민감하지 않음) |

#### 구현

```typescript
// logger.ts serializers
serializers: {
  req(request) {
    return {
      method: request.method,
      url: request.url,
      ip: request.ip,
      // body는 포함하지 않음 (비밀번호 등 민감 데이터)
    };
  },
}
```

### 5.3 에러 분류 체계

#### 서버 에러 응답 구조

```typescript
interface ErrorResponse {
  statusCode: number;
  error: string;       // HTTP 에러 이름
  message: string;     // 사용자 친화적 메시지
  details?: unknown;   // 추가 정보 (벌크 작업 실패 상세 등)
}
```

#### HttpError 코드 분류

| 코드 | 에러 | 사용 상황 |
|---|---|---|
| 400 | Bad Request | 검증 실패, 잘못된 파라미터 |
| 401 | Unauthorized | 인증 필요 (미로그인) |
| 403 | Forbidden | 권한 없음 (로그인했지만 Admin 아님), CSRF 실패 |
| 404 | Not Found | 리소스 없음 |
| 409 | Conflict | 중복, 제약조건 위반 (하위 카테고리 존재 등) |
| 413 | Payload Too Large | 파일 크기 초과 |
| 429 | Too Many Requests | Rate limit 초과 |
| 500 | Internal Server Error | 미처리 예외 |

#### 전역 에러 핸들러 (기존 구현 문서화)

```typescript
fastify.setErrorHandler((error, request, reply) => {
  // 1. HttpError → 해당 statusCode + message
  // 2. Fastify validation error → 400 + 검증 에러 상세
  // 3. 그 외 → 500 + 로그 기록 (스택 트레이스, 요청 정보, userId)
});
```

- 500 에러만 상세 로깅 (400/404 등은 정상 플로우)
- 프로덕션에서 500 에러 메시지를 클라이언트에 노출하지 않음 ("An unexpected error occurred")

### 5.5 헬스 체크 엔드포인트 (기존 구현 문서화)

| 경로 | 용도 | 응답 |
|---|---|---|
| `GET /health` | 기본 생존 확인 | `{ status: "ok" }` |
| `GET /api/health/live` | 버전 + 업타임 + 메모리 | `{ version, uptime, memory }` |
| `GET /api/health/ready` | DB 연결 확인 | 200 또는 503 |

- `/health`: 로드밸런서 기본 헬스 체크용
- `/api/health/live`: 서버 상태 상세 확인
- `/api/health/ready`: 서비스 준비 상태 (DB 포함)

### 컴포넌트 구조

| 계층 | 파일 | 역할 |
|---|---|---|
| 서버 | `plugins/logger.ts` | Pino 설정 (기존) |
| 서버 | `app.ts` | 전역 에러 핸들러 (기존) |
| 서버 | `app.ts` | 헬스 체크 라우트 (기존) |
| 서버 | `errors/http-error.ts` | HttpError 클래스 (기존) |

## 수용 기준

- [ ] 서버 로그가 dev에서 pretty(stdout), prod에서 JSON(stdout + error.log 파일)으로 출력된다
- [ ] 프로덕션에서 error 레벨 로그가 `logs/error.log` 파일에 기록된다
- [ ] test 환경에서 로그 레벨이 warn이고 요청 로깅이 비활성화된다
- [ ] 요청 body의 비밀번호 필드가 로그에 포함되지 않는다
- [ ] 기존 헤더 마스킹(authorization, cookie, set-cookie)이 유지된다
- [ ] 500 에러 발생 시 스택 트레이스와 요청 정보가 로깅된다
- [ ] 500 에러 응답에 내부 에러 메시지가 노출되지 않는다
- [ ] HttpError 코드별 분류가 올바르게 동작한다
- [ ] `logs/` 디렉토리가 `.gitignore`에 추가된다

## 의존성

- Blocked by: S-01
- Blocks: 없음

## 참고

- v1에서는 외부 모니터링 도구(Sentry, DataDog 등) 없이 자체 로깅으로 운영한다.
- 로그 파일 로테이션/보존은 인프라 레벨(logrotate 등)에서 관리한다.
- 클라이언트 에러 수집(React Error Boundary, API 에러 로깅)은 클라이언트 이슈에서 별도 처리한다.
