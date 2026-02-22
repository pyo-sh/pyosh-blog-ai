# Phase S-0: Fastify + Vitest 환경 구축 (2026-02-09)

## 작업 내용

### 1. 설치된 의존성

**Fastify 핵심:**

```
fastify: 5.7.4
zod: 3.25.76
fastify-type-provider-zod: 3.0.0
```

**Fastify 플러그인:**

```
@fastify/cors: 10.1.0
@fastify/cookie: 11.0.2
@fastify/session: 11.1.1
@fastify/multipart: 9.4.0
@fastify/swagger: 9.7.0
@fastify/swagger-ui: 5.2.5
pino-pretty: 13.1.3 (Fastify 기본 로거)
```

**테스트 프레임워크:**

```
vitest: 2.1.9
@vitest/ui: 2.1.9
@vitest/coverage-v8: 2.1.9
```

### 2. Vitest 설정

**vitest.config.ts:**

- Path alias 직접 설정 (@src, @test, @stub)
- ~~vite-tsconfig-paths 제거~~ (ESM only 패키지, CJS 환경 비호환)
- smoke test만 실행 (include: ["test/smoke.test.ts"])
- 기존 Mocha 테스트는 `pnpm test:mocha`로 유지

**package.json scripts:**

```json
{
  "test": "vitest",
  "test:watch": "vitest --watch",
  "test:ui": "vitest --ui",
  "test:coverage": "vitest --coverage",
  "test:mocha": "cross-env TS_NODE_PROJECT=tsconfig.test.json mocha"
}
```

### 3. Vitest 설정 이슈 해결

**문제:** vite-tsconfig-paths ESM only

```
ESM file cannot be loaded by `require`
```

**해결:** vitest.config.ts에서 path alias 직접 설정

```typescript
resolve: {
  alias: {
    "@src": path.resolve(__dirname, "./src"),
    "@test": path.resolve(__dirname, "./test"),
    "@stub": path.resolve(__dirname, "./stub"),
  },
}
```

### 4. 새 디렉토리 구조

```
server/src/
├── plugins/       # Fastify 플러그인 (typeorm, session, cors 등)
├── routes/        # 라우트 핸들러 (도메인별, controller 대체)
├── services/      # 비즈니스 로직 (도메인별)
├── schemas/       # Zod 스키마 (DTO 대체)
├── hooks/         # Fastify 훅 (auth, validation 등)
├── errors/        # 커스텀 에러 클래스
└── entities/      # TypeORM 엔티티 (유지)

# 레거시 (선택적 마이그레이션 후 삭제 예정)
├── core/          # 커스텀 프레임워크 (삭제 예정)
├── domains/       # User, Auth만 마이그레이션
├── loaders/       # plugins/로 대체
├── swagger/       # @fastify/swagger로 대체
├── constants/     # 필요한 것만 마이그레이션
└── utils/         # 필요한 것만 마이그레이션
```

### 5. 마이그레이션 전략 (선택적)

**도메인:**

- User, Auth만 마이그레이션 → routes/, services/
- 나머지 도메인은 일단 보류

**공통 모듈:**

- constants, utils 중 필요한 것만

**테스트:**

- setups, utils만 마이그레이션
- 도메인 테스트는 버림

**Stub:**

- 일단 유지 (Phase S-3에서 재검토)

### 6. Stub 유지 근거

- 타입 안전한 테스트 데이터 생성에 유용
- @faker-js/faker와 조합하여 사용 중
- Zod 스키마 도입 후 Factory 패턴으로 전환 검토 가능
- 현재는 잘 작동하므로 유지

### 7. tsconfig.json 확인

```json
{
  "experimentalDecorators": true, // TypeORM용 유지
  "emitDecoratorMetadata": true // TypeORM용 유지
}
```

Fastify는 decorator 불필요하지만 TypeORM이 필요로 함.

## 검증 결과

- ✅ Vitest smoke test 실행 성공
- ✅ Path alias 정상 작동
- ✅ TypeScript 컴파일 성공

## 교훈

### vite-tsconfig-paths 이슈

- ESM only 패키지는 CJS 환경(Vitest)에서 직접 import 불가
- resolve.alias로 직접 설정하는 것이 더 안정적

### 점진적 마이그레이션

- 기존 Mocha 테스트 유지하며 Vitest 병행 가능
- smoke test부터 시작하여 점진적 전환

## 다음 단계 (Phase S-1)

- [ ] Fastify 인스턴스 생성 (app.ts)
- [ ] plugins/typeorm.ts: TypeORM DataSource 연결
- [ ] plugins/session.ts: @fastify/cookie + @fastify/session
- [ ] plugins/cors.ts: @fastify/cors
- [ ] errors/http-error.ts: 커스텀 에러 + setErrorHandler
- [ ] schemas/common.ts: 공통 Zod 스키마
- [ ] server.ts: 서버 시작 + graceful shutdown

## 관련 파일

- `server/vitest.config.ts`
- `server/package.json`
- `server/test/smoke.test.ts`
