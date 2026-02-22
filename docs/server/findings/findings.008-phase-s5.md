# Phase S-5: 레거시 제거 - Express 완전 제거 (2026-02-10)

## 배경

Fastify 마이그레이션 완료 후 Express, 커스텀 프레임워크, Mocha 테스트 등 레거시 코드 제거.

## 작업 내용

### 1. 제거된 의존성

**Express 관련:**

```
express
express-session
express-async-errors
@types/express
@types/express-session
morgan
@types/morgan
body-parser
cookie-parser
```

**Passport 레거시:**

```
passport (0.7.0) → @fastify/passport로 대체됨
```

**검증 라이브러리:**

```
class-validator
class-transformer
```

**Swagger 레거시:**

```
swagger-express-ts (abandoned)
swagger-ui-express
```

**테스트 레거시:**

```
mocha
chai
chai-http
sinon
ts-mocha
@types/mocha
@types/chai
@types/sinon
```

**기타:**

```
multer → @fastify/multipart
reflect-metadata (일부 유지, TypeORM용)
```

### 2. 제거된 디렉토리 및 파일

```
server/src/
├── core/                    # 삭제 (커스텀 프레임워크)
│   ├── decorator/
│   ├── interface/
│   └── RouteContainer.ts
├── loaders/                 # 삭제 (plugins/로 대체됨)
│   ├── base.ts
│   ├── express.ts
│   ├── router.ts
│   ├── error-handler.ts
│   └── ...
├── swagger/                 # 삭제 (@fastify/swagger로 대체)
├── domains/                 # 대부분 삭제
│   ├── user/               # routes/user.ts로 마이그레이션
│   └── auth/               # routes/auth.ts로 마이그레이션

server/test/
├── *.test.ts               # Mocha 테스트 삭제
└── mocha.opts              # 삭제
```

### 3. 남은 디렉토리 (Fastify 구조)

```
server/src/
├── plugins/       # Fastify 플러그인
├── routes/        # 라우트 핸들러
├── services/      # 비즈니스 로직
├── schemas/       # Zod 스키마
├── hooks/         # Fastify 훅
├── errors/        # 커스텀 에러
├── entities/      # TypeORM 엔티티 (유지)
├── constants/     # 상수 (유지)
└── utils/         # 유틸리티 (유지)

server/test/
└── smoke.test.ts  # Vitest 테스트 (유지)
```

### 4. package.json scripts 정리

**제거:**

```json
{
  "test:mocha": "...",
  "test:mocha:watch": "..."
}
```

**유지/추가:**

```json
{
  "dev": "tsx watch src/server.ts",
  "build": "tsc",
  "start": "node dist/server.js",
  "test": "vitest",
  "test:watch": "vitest --watch",
  "test:ui": "vitest --ui",
  "test:coverage": "vitest --coverage"
}
```

### 5. tsconfig.json 변경

**제거 가능 (하지만 유지):**

```json
{
  "experimentalDecorators": true, // TypeORM 엔티티용 유지
  "emitDecoratorMetadata": true // TypeORM 엔티티용 유지
}
```

Drizzle로 마이그레이션 시 제거 가능.

## 의존성 감소 측정

| 구분            | Before   | After    | 감소            |
| --------------- | -------- | -------- | --------------- |
| dependencies    | 45개     | 28개     | **-17개**       |
| devDependencies | 32개     | 15개     | **-17개**       |
| **총 의존성**   | **77개** | **43개** | **-34개 (44%)** |

## LOC 감소 측정

| 구분     | Before     | After      | 감소      |
| -------- | ---------- | ---------- | --------- |
| src/     | ~2,464 LOC | ~1,200 LOC | **-51%**  |
| core/    | ~500 LOC   | 0 LOC      | **-100%** |
| loaders/ | ~300 LOC   | 0 LOC      | **-100%** |
| domains/ | ~800 LOC   | ~400 LOC   | **-50%**  |
| test/    | ~600 LOC   | ~100 LOC   | **-83%**  |

## 검증 결과

- ✅ `pnpm build` 성공
- ✅ `pnpm dev` 실행 성공
- ✅ `pnpm test` 통과
- ✅ 타입 오류 0개
- ✅ 린트 에러 0개

## 핵심 인사이트

### 커스텀 프레임워크 제거 효과

- 500 LOC 감소
- 유지보수 포인트 제거
- 표준 Fastify 패턴으로 전환

### Express → Fastify 전환 효과

- 17개 의존성 제거
- 성능 2-3배 향상 (Fastify 벤치마크)
- 타입 안전성 개선

### class-validator → Zod 전환 효과

- 타입 추론 자동화
- 런타임 성능 향상
- 보일러플레이트 감소

### Mocha → Vitest 전환 효과

- 테스트 실행 속도 향상
- ESM 네이티브 지원
- TypeScript 통합 개선

## 교훈

- 커스텀 프레임워크는 초기엔 유연하나 장기적으로 부담
- 표준 도구 사용이 유지보수에 유리
- 의존성 감소는 보안, 빌드 속도에 긍정적 영향

## 다음 단계 (Phase S-6)

- [ ] Drizzle ORM 검토
- [ ] TypeORM → Drizzle 마이그레이션
- [ ] experimentalDecorators 제거

## 관련 파일

- `server/package.json` (의존성 대폭 감소)
- `server/src/` (구조 단순화)
