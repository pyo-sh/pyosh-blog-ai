# Server 마이그레이션 방향 결정 - Fastify 채택 (2026-02-09)

## 배경

Express 5.x로 업그레이드 후, 장기적인 서버 아키텍처 방향 결정 필요. 커스텀 프레임워크 유지 vs 교체 검토.

## 현재 서버 코드베이스 분석

### 규모

| 지표            | 수치             |
| --------------- | ---------------- |
| 소스 파일 (.ts) | 63개             |
| 총 LOC (src/)   | ~2,464           |
| 컨트롤러        | 2개 (User, Auth) |
| 서비스          | 1개 (User)       |
| 리포지토리      | 7개              |
| 엔티티          | 8개              |
| 도메인          | 9개              |
| 테스트 파일     | 10개             |

### 커스텀 프레임워크 복잡도

- RouteContainer.ts: 380줄 (DI 컨테이너 + 라우터 생성)
- 데코레이터 7개 파일: ~120줄
- Reflect Metadata 기반 런타임 인트로스펙션
- 2단계 등록: 메타데이터 → 인스턴스 생성
- 프로퍼티 기반 DI (테스트용 dynamic getters)

## 마이그레이션 방향 비교

### Option 1: NestJS 전환

**장점:**

- 현재 구조와 유사한 API
- 풍부한 에코시스템
- @nestjs/swagger 즉시 사용
- 구조화된 모듈 시스템

**단점:**

- experimentalDecorators 종속 지속
- 블로그 API에 과도한 무게
- Express 5.x 공식 미지원
- vendor lock-in 심화

### Option 2: Fastify + Zod + Clean Architecture (채택)

**장점:**

- TC39 표준 부합
- Zod 압도적 TypeScript 타입 추론
- Express 대비 2-3배 성능
- 경량화, 의존성 최소화
- 순수 함수 기반 테스트 용이

**단점:**

- 구조 직접 설계 필요
- 커스텀 프레임워크 전면 재작성
- TypeORM 엔티티와 패러다임 혼재

## 결정 사항

**Option 2 채택** — Fastify 5.x + Zod + Clean Architecture + Vitest

### 핵심 근거

1. **규모**: 컨트롤러 2개, 서비스 1개 규모에 NestJS는 과도함
2. **표준 준수**: `experimentalDecorators`는 TC39 표준과 상충
3. **유지보수**: 커스텀 프레임워크(~500 LOC) 제거로 부담 해소
4. **Swagger**: Zod 스키마에서 자동 생성으로 abandoned swagger-express-ts 교체
5. **일관성**: Client 현대화(App Router, TailwindCSS)와 동일한 방향성

## 기술 스택 변경

| 항목        | Before (Express)            | After (Fastify)                        |
| ----------- | --------------------------- | -------------------------------------- |
| 프레임워크  | Express 5                   | Fastify 5.x                            |
| 검증        | class-validator/transformer | Zod                                    |
| API 문서    | swagger-express-ts          | @fastify/swagger + @fastify/swagger-ui |
| 테스트      | Mocha/Chai/Sinon            | Vitest                                 |
| 인증        | Passport.js                 | @fastify/passport 또는 커스텀 훅       |
| 세션        | express-session             | @fastify/session + @fastify/cookie     |
| 파일 업로드 | multer                      | @fastify/multipart                     |
| 에러 처리   | express-async-errors        | Fastify 내장                           |

## 마이그레이션 계획

### Phase S-0: 환경 구축

- Fastify + Vitest 설치
- 기본 설정 파일 생성

### Phase S-1: 인프라

- Fastify 플러그인 (typeorm, session, cors)
- 에러 핸들링
- Health check

### Phase S-2: 인증

- @fastify/passport 설정
- GitHub/Google OAuth
- Session 관리

### Phase S-3: User 도메인 마이그레이션

- routes/user.ts
- services/user.ts
- Zod 스키마

### Phase S-4: Auth 도메인 마이그레이션

- routes/auth.ts
- OAuth 콜백 처리

### Phase S-5: 레거시 제거

- Express 완전 제거
- 커스텀 프레임워크 삭제
- Mocha 테스트 제거

### Phase S-6: Drizzle ORM (선택)

- TypeORM → Drizzle 마이그레이션 검토

## 아키텍처 원칙

### Vertical Slice Architecture (기능 중심)

- **No Repository Layer**: Drizzle 자체가 충분히 추상화
- **Function-based**: 클래스 지양, 함수형 모듈
- **Module 단위**: `src/modules/{feature}/` 안에 routes, service, schema, test 포함

### 구조 예시

```
server/src/
├── plugins/       # Fastify 플러그인
├── routes/        # 라우트 핸들러
├── services/      # 비즈니스 로직
├── schemas/       # Zod 스키마
├── hooks/         # Fastify 훅
├── errors/        # 커스텀 에러
└── entities/      # TypeORM 엔티티 (유지)
```

## 예상 타임라인

- Phase S-0: 1일
- Phase S-1: 1일
- Phase S-2: 1-2일
- Phase S-3: 1일
- Phase S-4: 1일
- Phase S-5: 1일
- **총 예상 기간: 5-7일**

## 리스크 관리

| 리스크                      | 대응 방안                             |
| --------------------------- | ------------------------------------- |
| Fastify 러닝 커브           | 공식 문서 충실, 예제 프로젝트 참고    |
| Zod vs class-validator 차이 | Zod 스키마 직접 작성 (타입 추론 우수) |
| TypeORM 유지 문제           | Phase S-6에서 Drizzle 전환 검토       |
| 테스트 재작성 부담          | Vitest migration 도구 활용            |

## 교훈

- 커스텀 프레임워크는 초기엔 유연하나 장기적으로 부담
- 표준(TC39)을 따르는 것이 유지보수에 유리
- 규모가 작을수록 경량 프레임워크가 적합

## 관련 파일

- `server/src/core/` (삭제 예정)
- `server/src/loaders/` (plugins/로 대체 예정)
