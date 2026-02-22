# Phase S-2: 인증 시스템 전환 (2026-02-10)

## 배경

Express + Passport.js 기반 OAuth 인증 시스템을 Fastify로 전환. GitHub, Google OAuth 2.0 지원.

## 작업 내용

### 1. @fastify/passport 설치

```
@fastify/passport: 3.1.0
@fastify/secure-session: 8.2.1 (선택적, 고성능 세션)
passport-github2: 0.1.12
passport-google-oauth20: 2.0.0
```

### 2. 생성된 파일

**plugins/passport.ts:**

- Fastify Passport 플러그인
- GitHub, Google Strategy 설정
- serializeUser, deserializeUser

**routes/auth/index.ts:**

- GET /auth/github - GitHub OAuth 시작
- GET /auth/github/callback - GitHub OAuth 콜백
- GET /auth/google - Google OAuth 시작
- GET /auth/google/callback - Google OAuth 콜백
- POST /auth/logout - 로그아웃

**hooks/auth.hook.ts:**

- preHandler 훅으로 인증 체크
- req.user 존재 여부 검증

### 3. Passport 플러그인 구현

```typescript
export default fp(async (fastify: FastifyInstance) => {
  await fastify.register(fastifyPassport.initialize());
  await fastify.register(fastifyPassport.secureSession());

  // GitHub Strategy
  fastifyPassport.use(
    "github",
    new GitHubStrategy(
      {
        clientID: process.env.GITHUB_CLIENT_ID!,
        clientSecret: process.env.GITHUB_CLIENT_SECRET!,
        callbackURL: process.env.GITHUB_CALLBACK_URL!,
      },
      async (accessToken, refreshToken, profile, done) => {
        // User 조회 또는 생성
        const user = await findOrCreateUser(profile);
        done(null, user);
      },
    ),
  );

  // Google Strategy (동일 패턴)

  fastifyPassport.registerUserSerializer(async (user) => user.id);
  fastifyPassport.registerUserDeserializer(async (id) => {
    return await fastify.db
      .getRepository(UserEntity)
      .findOne({ where: { id } });
  });
});
```

### 4. 인증 라우트

```typescript
export default async function authRoutes(fastify: FastifyInstance) {
  // GitHub OAuth
  fastify.get(
    "/auth/github",
    { preValidation: fastifyPassport.authenticate("github") },
    async (req, reply) => {},
  );

  fastify.get(
    "/auth/github/callback",
    {
      preValidation: fastifyPassport.authenticate("github", {
        successRedirect: "/",
        failureRedirect: "/login",
      }),
    },
    async (req, reply) => {},
  );

  // Google OAuth (동일 패턴)

  // Logout
  fastify.post(
    "/auth/logout",
    { preHandler: requireAuth },
    async (req, reply) => {
      req.logout();
      reply.send({ message: "Logged out" });
    },
  );
}
```

### 5. 인증 훅

```typescript
export async function requireAuth(req: FastifyRequest, reply: FastifyReply) {
  if (!req.user) {
    throw HttpError.unauthorized("로그인이 필요합니다");
  }
}

// 사용 예시
fastify.get("/profile", { preHandler: requireAuth }, async (req, reply) => {
  return { user: req.user };
});
```

## 검증 결과

- ✅ Passport 플러그인 로딩 성공
- ✅ OAuth 라우트 등록 성공
- ✅ 인증 훅 동작 확인
- 🔲 실제 OAuth 플로우는 환경변수 설정 후 수동 테스트 필요

## 핵심 인사이트

### Express Passport vs Fastify Passport

| 항목   | Express                         | Fastify                                           |
| ------ | ------------------------------- | ------------------------------------------------- |
| 초기화 | app.use(passport.initialize())  | fastify.register(fastifyPassport.initialize())    |
| 세션   | app.use(passport.session())     | fastify.register(fastifyPassport.secureSession()) |
| 인증   | passport.authenticate("github") | fastifyPassport.authenticate("github")            |
| 직렬화 | passport.serializeUser()        | fastifyPassport.registerUserSerializer()          |

### preValidation vs preHandler

- **preValidation**: 라우트 핸들러 실행 전, 검증 단계
- **preHandler**: 검증 후, 핸들러 실행 직전
- Passport authenticate는 preValidation에서 실행

### @fastify/secure-session

- express-session보다 빠름 (메모리 기반)
- TypeORM store 대신 사용 가능
- 하지만 세션 영속성 필요 시 TypeORM store 유지 권장

## 이슈 및 해결

### 이슈 1: req.user 타입 불일치

**문제:**

```typescript
// @fastify/passport가 req.user를 passport.User로 선언
// 하지만 실제로는 UserEntity
```

**해결:**

```typescript
// types/fastify.d.ts
declare module "fastify" {
  interface PassportUser extends UserEntity {}
}
```

### 이슈 2: Strategy callback 비동기 처리

**문제:** TypeORM 조회가 비동기인데 done() 호출 타이밍 불명확

**해결:**

```typescript
async (accessToken, refreshToken, profile, done) => {
  try {
    const user = await findOrCreateUser(profile);
    done(null, user);
  } catch (error) {
    done(error as Error);
  }
};
```

## 교훈

- Fastify Passport는 Express Passport와 API가 거의 동일
- preValidation 훅이 인증 체크에 적합
- TypeORM과의 통합은 UserDeserializer에서 처리

## 다음 단계 (Phase S-3)

- [ ] routes/user.ts: User CRUD 라우트
- [ ] services/user.ts: User 비즈니스 로직
- [ ] schemas/user.ts: Zod 스키마

## 관련 파일

- `server/src/plugins/passport.ts`
- `server/src/routes/auth/index.ts`
- `server/src/hooks/auth.hook.ts`
- `server/types/fastify.d.ts`
