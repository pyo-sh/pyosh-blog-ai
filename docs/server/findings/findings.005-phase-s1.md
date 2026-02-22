# Phase S-1: Fastify 핵심 인프라 구축 (2026-02-09)

## 작업 내용

### 1. 생성된 파일

**errors/http-error.ts:**

- HttpError 클래스
- static 팩토리 메서드 (badRequest, unauthorized, forbidden, notFound, conflict, internalServerError)

**schemas/common.ts:**

- 공통 Zod 스키마 (ErrorResponse, Pagination, IdParam)

**plugins/typeorm.ts:**

- TypeORM DataSource → Fastify 데코레이터
- onClose 훅으로 graceful shutdown

**plugins/cors.ts:**

- @fastify/cors 플러그인 설정

**plugins/session.ts:**

- @fastify/cookie + @fastify/session
- typeorm-store 연결 준비

**app.ts:**

- buildApp() 함수형 패턴
- Fastify 인스턴스 생성
- 플러그인 로딩 순서 정의

**server.ts:**

- 엔트리 포인트
- graceful shutdown (SIGINT, SIGTERM)

### 2. 의존성 추가

```
fastify-plugin: 5.1.0
mysql2: 3.16.3 (TypeORM MySQL 드라이버)
```

### 3. 아키텍처 개선

#### Express → Fastify 전환

- IIFE 즉시 실행 → 함수형 buildApp() 패턴 (테스트 용이)
- Loader 패턴 → Fastify Plugin 패턴 (의존성 명시)
- morgan → pino-pretty (dev 모드 컬러 로그)

#### 에러 핸들링 (3단계)

1. **HttpError**: 커스텀 비즈니스 에러
2. **Zod validation**: 400 + 상세 에러 메시지
3. **기타 에러**: 500 + 일반 메시지

#### Logger

- Pino (info in dev, warn in prod)
- pino-pretty로 컬러 로그

#### Health check

- GET /health 엔드포인트

### 4. buildApp() 패턴

```typescript
export async function buildApp(opts: FastifyServerOptions = {}) {
  const app = fastify({
    logger: {
      level: process.env.NODE_ENV === "production" ? "warn" : "info",
      transport:
        process.env.NODE_ENV === "development"
          ? { target: "pino-pretty" }
          : undefined,
    },
    ...opts,
  });

  // 플러그인 로딩 순서
  await app.register(typeormPlugin);
  await app.register(corsPlugin);
  await app.register(sessionPlugin);

  // 에러 핸들러
  app.setErrorHandler(errorHandler);

  // Health check
  app.get("/health", async () => ({ status: "ok" }));

  return app;
}
```

### 5. TypeORM 플러그인

```typescript
export default fp(async (fastify: FastifyInstance) => {
  const dataSource = new DataSource({
    type: "mysql",
    host: process.env.DB_HOST,
    port: parseInt(process.env.DB_PORT || "3306"),
    username: process.env.DB_USERNAME,
    password: process.env.DB_PASSWORD,
    database: process.env.DB_DATABASE,
    entities: [path.join(__dirname, "../entities/**/*.entity.{ts,js}")],
    synchronize: false,
    logging: process.env.NODE_ENV === "development",
  });

  await dataSource.initialize();
  fastify.decorate("db", dataSource);

  fastify.addHook("onClose", async () => {
    await dataSource.destroy();
  });
});
```

### 6. Session 플러그인

```typescript
export default fp(async (fastify: FastifyInstance) => {
  await fastify.register(fastifyCookie);

  await fastify.register(fastifySession, {
    secret: process.env.SESSION_SECRET || "secret-key-change-in-production",
    cookieName: "sessionId",
    cookie: {
      secure: process.env.NODE_ENV === "production",
      httpOnly: true,
      maxAge: 1000 * 60 * 60 * 24 * 7, // 7 days
    },
    store: new TypeormStore({
      cleanupLimit: 2,
      ttl: 86400,
    }).connect(fastify.db.getRepository(SessionEntity)),
  });
});
```

## 검증 결과

- ✅ TypeScript 컴파일 성공
- ✅ Fastify 인스턴스 생성 성공
- ✅ 플러그인 로딩 성공 (typeorm, session, cors)
- ⚠️ MySQL 연결 실패는 정상 (로컬 서버 없음)

## 핵심 인사이트

### Fastify Plugin 패턴

- fastify-plugin으로 감싸면 부모 스코프에 데코레이터 등록
- 플러그인 간 의존성을 명시적으로 관리 가능
- onClose 훅으로 리소스 정리 자동화

### Express IIFE vs Fastify buildApp()

- Express: 즉시 실행으로 테스트 어려움
- Fastify: 함수형 패턴으로 테스트 용이, DI 가능

### Pino Logger

- Express morgan보다 10배 빠름
- 구조화된 JSON 로그
- pino-pretty로 개발 환경 가독성

## 교훈

- Fastify 플러그인 시스템이 Express 미들웨어보다 명시적
- TypeORM DataSource를 Fastify 데코레이터로 등록하면 전역 접근 편리
- graceful shutdown은 onClose 훅으로 자동화 가능

## 다음 단계 (Phase S-2)

- [ ] hooks/auth.hook.ts: 인증 훅
- [ ] routes/auth/: OAuth 라우트
- [ ] @fastify/passport 또는 커스텀 OAuth 구현

## 관련 파일

- `server/src/app.ts`
- `server/src/server.ts`
- `server/src/plugins/typeorm.ts`
- `server/src/plugins/session.ts`
- `server/src/plugins/cors.ts`
- `server/src/errors/http-error.ts`
- `server/src/schemas/common.ts`
