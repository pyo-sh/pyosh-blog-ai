# Server 기술 스택 분석 (2026-02-06)

## 배경

3년간 방치된 블로그 프로젝트 Server의 현재 상태 파악 및 현대화 전략 수립을 위한 초기 분석.

## 핵심 기술 스택

### 프레임워크

- **Express 4.18.2**
- **TypeScript 4.9.5** (strict mode)
- **TypeORM 0.3.12**
  - typeorm-naming-strategies (snake_case)
  - Soft delete 지원

### 커스텀 프레임워크

**NestJS-style Decorator 시스템** (직접 구현)

- `@Controller`, `@Get`, `@Post`, `@Put`, `@Delete`
- `@Param`, `@Body`, `@Res`, `@Req`
- `@Injectable` (DI 컨테이너)
- Reflect Metadata 사용

### 인증 & 세션

- **Passport.js**
  - passport-github
  - passport-google-oauth20
- **express-session** + typeorm-store
- Cookie 기반 세션

### 유효성 검사

- **class-validator**
- **class-transformer**
- DTO 패턴 적용

### 테스트

- **Mocha + Chai**
- ts-mocha
- Sinon (mocking)
- Supertest (HTTP 테스트)

### API 문서

- **swagger-express-ts**
- swagger-ui-express

## 프로젝트 구조

```
server/src/
├── domains/              # 도메인별 모듈
│   ├── user/
│   │   ├── user.controller.ts
│   │   ├── user.service.ts
│   │   ├── user.repository.ts
│   │   └── models/       # DTOs
│   ├── post/
│   ├── auth/
│   └── ...
├── entities/             # TypeORM 엔티티
├── core/                 # 커스텀 프레임워크
│   ├── decorator/
│   ├── interface/
│   └── RouteContainer.ts
├── loaders/              # 앱 초기화 로직
│   ├── base.ts
│   ├── typeorm.ts
│   ├── session.ts
│   ├── passport.ts
│   ├── router.ts
│   └── error-handler.ts
└── app.ts                # 엔트리 포인트
```

## 아키텍처 패턴

### Domain-Driven Design

- domains 폴더에 기능별 모듈화

### Layered Architecture

- Controller (HTTP 요청 처리)
- Service (비즈니스 로직)
- Repository (데이터 접근)
- Entity (데이터 모델)

### DTO Pattern

- 입력 검증용 별도 모델

### Dependency Injection

- 커스텀 DI 컨테이너

## Decorator 기반 라우팅

```typescript
@Controller("/user")
class UserController {
  constructor(private readonly userService: UserService) {}

  @Get("/:id")
  async getUser(
    @Param("id", { validObject: UserIdParam }) id: number,
    @Res() res: Response,
  ) {
    const user = await this.userService.getUser(id);
    return res.status(200).send({ user });
  }
}
```

## 발견된 이슈

### 버전 이슈

- TypeORM 0.3.12 → 0.3.x latest
- TypeScript 4.9.5 → 5.x
- Node.js 버전 확인 필요

### 보안 이슈

- .env 파일들이 git에 포함됨
- 세션 보안 설정 확인 필요

### 코드 품질

- TODO 주석 다수
- Test 커버리지 확인 필요
- API 문서 자동화 상태 확인 필요

## 현대화 검토 항목

1. 커스텀 프레임워크 vs NestJS 교체 검토
2. TypeORM vs Prisma/Drizzle 비교 검토
3. swagger-express-ts (abandoned) 교체
4. 의존성 업데이트 전략
5. 테스트 프레임워크 현대화 (Vitest)

## 커스텀 프레임워크 복잡도

- RouteContainer.ts: 380줄 (DI 컨테이너 + 라우터 생성)
- 데코레이터 7개 파일: ~120줄
- Reflect Metadata 기반 런타임 인트로스펙션
- 2단계 등록: 메타데이터 → 인스턴스 생성
- 프로퍼티 기반 DI (테스트용 dynamic getters)

## 관련 파일

- `server/package.json`
- `server/tsconfig.json`
- `server/src/core/`
- `server/src/domains/`
