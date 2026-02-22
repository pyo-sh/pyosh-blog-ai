# Phase S-3: User 도메인 마이그레이션 - Zod 이슈 (2026-02-10)

## 배경

User 도메인을 Express controller/service에서 Fastify route/service로 마이그레이션. Zod 스키마 기반 검증 도입 과정에서 fastify-type-provider-zod 이슈 발견.

## 작업 내용

### 1. 생성된 파일

**schemas/user.ts:**

- UserCreateSchema, UserUpdateSchema
- UserResponseSchema, UserListResponseSchema
- Zod로 타입 정의 및 검증

**routes/user.ts:**

- GET /user - User 목록
- GET /user/:id - User 조회
- POST /user - User 생성
- PUT /user/:id - User 수정
- DELETE /user/:id - User 삭제

**services/user.ts:**

- findUsers, findUserById, createUser, updateUser, deleteUser
- TypeORM Repository 사용

### 2. Zod 스키마 예시

```typescript
export const UserCreateSchema = z.object({
  email: z.string().email(),
  name: z.string().min(2).max(50),
  avatarUrl: z.string().url().optional(),
});

export const UserResponseSchema = z.object({
  id: z.number(),
  email: z.string(),
  name: z.string(),
  avatarUrl: z.string().nullable(),
  createdAt: z.date(),
  updatedAt: z.date(),
});

export type UserCreate = z.infer<typeof UserCreateSchema>;
export type UserResponse = z.infer<typeof UserResponseSchema>;
```

### 3. Fastify Route with Zod

```typescript
export default async function userRoutes(fastify: FastifyInstance) {
  // GET /user/:id
  fastify.get<{ Params: { id: string } }>(
    "/user/:id",
    {
      schema: {
        params: z.object({ id: z.string().regex(/^\d+$/) }),
        response: {
          200: UserResponseSchema,
        },
      },
    },
    async (req, reply) => {
      const id = parseInt(req.params.id);
      const user = await userService.findUserById(fastify.db, id);
      return reply.send(user);
    },
  );

  // POST /user
  fastify.post<{ Body: UserCreate }>(
    "/user",
    {
      schema: {
        body: UserCreateSchema,
        response: {
          201: UserResponseSchema,
        },
      },
    },
    async (req, reply) => {
      const user = await userService.createUser(fastify.db, req.body);
      return reply.status(201).send(user);
    },
  );
}
```

## 발견된 이슈

### fastify-type-provider-zod JSON Schema 변환 실패

**문제:**

```
ZodToJsonSchemaError: Cannot convert nested discriminated unions to JSON Schema
```

**원인:**

- fastify-type-provider-zod는 Zod 스키마를 JSON Schema로 변환
- 일부 Zod 기능(discriminatedUnion, transform 등)은 JSON Schema로 변환 불가
- Fastify는 내부적으로 JSON Schema 검증 사용

**영향받는 스키마:**

- discriminatedUnion
- z.transform()
- z.refine() (일부)
- z.lazy()

### 해결 방법 (채택: Option 2)

#### Option 1: JSON Schema 직접 작성 (비권장)

```typescript
{
  schema: {
    body: {
      type: "object",
      properties: {
        email: { type: "string", format: "email" },
        name: { type: "string", minLength: 2, maxLength: 50 },
      },
      required: ["email", "name"],
    },
  },
}
```

- **단점**: Zod 타입 추론 못 씀, 중복 작성

#### Option 2: 수동 검증 (채택)

```typescript
fastify.post<{ Body: UserCreate }>("/user", async (req, reply) => {
  // 수동 Zod 검증
  const parsed = UserCreateSchema.parse(req.body);
  const user = await userService.createUser(fastify.db, parsed);
  return reply.status(201).send(user);
});
```

- **장점**: Zod 타입 추론 유지, 모든 Zod 기능 사용 가능
- **단점**: Swagger 자동 생성 안 됨, 수동 에러 핸들링 필요

#### Option 3: zod-to-json-schema 직접 사용

```typescript
import { zodToJsonSchema } from "zod-to-json-schema";

{
  schema: {
    body: zodToJsonSchema(UserCreateSchema),
  },
}
```

- **문제**: 동일한 변환 실패 발생

## 수동 검증 패턴 (최종 채택)

```typescript
// 공통 Zod 검증 헬퍼
export function validateBody<T>(schema: z.ZodSchema<T>) {
  return async (req: FastifyRequest, reply: FastifyReply) => {
    try {
      req.body = schema.parse(req.body);
    } catch (error) {
      if (error instanceof z.ZodError) {
        throw HttpError.badRequest(error.errors[0].message);
      }
      throw error;
    }
  };
}

// 사용 예시
fastify.post<{ Body: UserCreate }>(
  "/user",
  { preHandler: validateBody(UserCreateSchema) },
  async (req, reply) => {
    const user = await userService.createUser(fastify.db, req.body);
    return reply.status(201).send(user);
  },
);
```

## 검증 결과

- ✅ User CRUD 라우트 동작 확인
- ✅ Zod 수동 검증 패턴 동작
- ⚠️ Swagger 자동 생성은 불가 (수동 작성 필요)
- ✅ TypeScript 타입 추론 정상

## 핵심 인사이트

### class-validator vs Zod

| 항목             | class-validator            | Zod                                |
| ---------------- | -------------------------- | ---------------------------------- |
| 타입 추론        | 수동 타입 선언 필요        | 자동 타입 추론 ✅                  |
| 검증 위치        | 데코레이터 (클래스)        | 스키마 (함수)                      |
| Fastify 통합     | 수동 구현 필요             | fastify-type-provider-zod (제한적) |
| JSON Schema 변환 | class-validator-jsonschema | zod-to-json-schema (제한적)        |
| 런타임 성능      | 느림                       | 빠름 ✅                            |

### Zod의 장점

- 타입스크립트 타입 추론 압도적
- 함수형, 조합 가능
- transform, refine 등 강력한 기능

### Zod의 단점

- Fastify JSON Schema 변환 제한
- Swagger 자동 생성 어려움
- 수동 검증 필요 시 보일러플레이트 증가

## 교훈

- fastify-type-provider-zod는 단순 스키마에만 적합
- 복잡한 검증은 수동 Zod 검증 + preHandler 패턴 사용
- Swagger가 필수라면 JSON Schema 직접 작성 고려
- 타입 안전성을 우선한다면 Zod 수동 검증이 최선

## 대안 검토

### drizzle-zod 사용

- Drizzle ORM 스키마에서 Zod 스키마 자동 생성
- Phase S-6 (Drizzle 마이그레이션)에서 재검토

## 다음 단계 (Phase S-4)

- [ ] routes/auth.ts 추가 (비밀번호 변경 등)
- [ ] 통합 테스트 작성
- [ ] Phase S-5로 이동 (레거시 제거)

## 관련 파일

- `server/src/schemas/user.ts`
- `server/src/routes/user.ts`
- `server/src/services/user.ts`
