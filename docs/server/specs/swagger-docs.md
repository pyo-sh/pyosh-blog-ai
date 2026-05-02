# F-37: Swagger 세부화

**상태:** DONE
**최종 수정:** 2026-05-02

---

## 1. 개요

Swagger UI를 통해 사람이 API를 바로 테스트할 수 있는 완전한 문서화 환경을 구축한다. 모든 엔드포인트에 예시 데이터, 인증 요구사항, CSRF 요구사항, rate limit 정보를 추가하여 "Try it out"으로 즉시 테스트 가능하게 한다.

## 2. 배경 및 동기

현재 41개 엔드포인트에 Zod 스키마 기반 요청/응답 검증이 100% 적용되어 있으나, Swagger UI에서 실제 테스트하기에는 부족한 점이 있다:

- 예시 데이터가 없어 "Try it out" 시 빈 템플릿만 표시됨
- 22개 인증 라우트에 security 선언이 없어 자물쇠 아이콘 미표시
- CSRF 보호가 필요한 라우트에 해당 정보 미표시
- 라우트별 rate limit이 OpenAPI 스펙에 없음
- 태그 상위 정의가 `auth`, `health`만 있어 그룹핑 불완전
- 파일 업로드 스키마가 OpenAPI 3.0이 아닌 Swagger 2.0 문법 사용
- 프로덕션에서 Swagger UI 비활성화 로직 없음

## 3. 목표

- 모든 스키마에 예시 데이터와 필드 설명을 추가한다
- 인증 라우트에 `security` 선언을 추가한다
- CSRF, rate limit 요구사항을 문서에 명시한다
- 태그 목록을 전체 리소스로 확장한다
- 파일 업로드 스키마를 OpenAPI 3.0 규격으로 수정한다
- 프로덕션 환경에서 Swagger UI를 비활성화한다
- API 소비자가 이 문서만으로 모든 엔드포인트를 테스트할 수 있도록 한다

## 4. 비목표

- OpenAPI 스펙 버전 업그레이드 (3.0.0 유지)
- API 버전 관리 (v1/v2 경로 분리)
- 외부 API 문서 사이트 생성 (Swagger UI 내장으로 충분)

---

## 5. 상세 설계

### 5.1 예시 데이터 추가

#### 방법: Zod `.describe()` + `.openapi()`

`fastify-type-provider-zod`는 Zod 스키마의 `.describe()`를 OpenAPI `description`으로, `zod-openapi`의 `.openapi({ example })` 을 OpenAPI `example`로 변환한다.

**필드별 설명 추가:**

```typescript
// 변경 전
export const PostSlugParamSchema = z.object({
  slug: z.string().min(1),
});

// 변경 후
export const PostSlugParamSchema = z.object({
  slug: z.string().min(1).describe("게시글 고유 슬러그"),
});
```

**스키마 전체 예시 추가:**

```typescript
// 변경 전
export const CreatePostBodySchema = z.object({
  title: z.string().min(1).max(200),
  contentMd: z.string().min(1),
  categoryId: z.number().int().positive(),
  // ...
});

// 변경 후
export const CreatePostBodySchema = z.object({
  title: z.string().min(1).max(200).describe("게시글 제목"),
  contentMd: z.string().min(1).describe("마크다운 본문"),
  categoryId: z.number().int().positive().describe("카테고리 ID"),
  thumbnailUrl: ThumbnailUrlInputSchema
    .optional()
    .describe("썸네일 URL (/uploads/... 또는 http(s) URL)"),
  visibility: z.enum(["public", "private"])
    .optional()
    .default("public")
    .describe("공개 범위"),
  status: z.enum(["draft", "published", "archived"])
    .optional()
    .default("draft")
    .describe("게시 상태"),
  tags: z.array(z.string().min(1).max(30))
    .optional()
    .describe("태그 이름 배열"),
  publishedAt: z.string().datetime()
    .optional()
    .describe("발행일 (ISO 8601)"),
});
```

#### 적용 대상

모든 스키마 파일에 `.describe()`를 추가한다:

| 스키마 파일 | 스키마 수 |
|---|---|
| `routes/posts/post.schema.ts` | 10 |
| `routes/comments/comment.schema.ts` | 8 |
| `routes/guestbook/guestbook.schema.ts` | 6 |
| `routes/categories/category.schema.ts` | 5 |
| `routes/assets/asset.schema.ts` | 4 |
| `routes/tags/tag.schema.ts` | 2 |
| `routes/stats/stats.schema.ts` | 3 |
| `routes/user/user.schema.ts` | 3 |
| `schemas/common.ts` | 4 |

### 5.2 인증 문서화

#### security 선언 추가

22개 인증 라우트에 `security` 필드를 추가하여 Swagger UI에 자물쇠 아이콘이 표시되도록 한다.

**requireAdmin 라우트 (19개):**

```typescript
// 변경 전
{
  preHandler: requireAdmin(adminService),
  schema: {
    tags: ["posts", "admin"],
    summary: "Get all posts (Admin)",
  },
}

// 변경 후
{
  preHandler: requireAdmin(adminService),
  schema: {
    tags: ["posts", "admin"],
    summary: "Get all posts (Admin)",
    security: [{ cookieAuth: [] }],
  },
}
```

**requireAuth 라우트 (3개):**

동일하게 `security: [{ cookieAuth: [] }]` 추가.

#### 인증 방식별 분류

| 인증 방식 | 라우트 수 | security scheme |
|---|---|---|
| `requireAdmin` (세션 기반) | 19 | `cookieAuth` |
| `requireAuth` (OAuth 기반) | 3 | `cookieAuth` |
| Public (인증 없음) | 19 | 없음 |

### 5.3 CSRF 요구사항 문서화

CSRF 보호가 필요한 state-changing 라우트(POST, PUT, PATCH, DELETE)에 다음을 추가한다:

1. **description에 CSRF 안내 추가:**

```typescript
description: "게시글을 생성합니다. Admin 권한 필요.\n\n" +
  "**CSRF 토큰 필요**: `GET /api/auth/csrf-token`으로 토큰을 발급받아 " +
  "`x-csrf-token` 헤더에 포함해야 합니다.",
```

2. **CSRF 토큰 발급 엔드포인트의 description 보강:**

토큰 사용 방법, 유효 기간, 헤더 이름을 명시한다.

### 5.4 Rate limit 문서화

라우트별 rate limit을 description에 명시한다.

| 라우트 | rate limit |
|---|---|
| `POST /api/auth/admin/login` | 5회/분 |
| `POST /api/posts/:postId/comments` | 10회/분 |
| `POST /api/guestbook` | 10회/분 |
| `POST /api/stats/view` | 10회/분 |
| 기타 전체 | 100회/분 (글로벌) |

```typescript
description: "게시글에 댓글을 작성합니다.\n\n" +
  "**Rate limit**: 10회/분",
```

### 5.5 태그 목록 확장

Swagger 플러그인의 태그 정의를 전체 리소스로 확장한다.

```typescript
tags: [
  { name: "auth", description: "인증 (Admin 로그인, OAuth, CSRF)" },
  { name: "health", description: "헬스 체크" },
  { name: "posts", description: "게시글 CRUD" },
  { name: "comments", description: "댓글 조회/작성/삭제" },
  { name: "guestbook", description: "방명록 조회/작성/삭제" },
  { name: "categories", description: "카테고리 관리" },
  { name: "assets", description: "파일 업로드/관리" },
  { name: "tags", description: "태그 조회" },
  { name: "stats", description: "통계 (조회수, 대시보드)" },
  { name: "user", description: "OAuth 사용자 프로필" },
  { name: "admin", description: "Admin 전용 엔드포인트 (다른 태그와 함께 사용)" },
  { name: "seo", description: "sitemap.xml, rss.xml" },
],
```

### 5.6 파일 업로드 스키마 수정

현재 `consumes: ["multipart/form-data"]`는 Swagger 2.0 문법이다. OpenAPI 3.0 규격에 맞게 `requestBody`로 변경하고, 제한사항을 문서화한다.

**문서화할 제한사항:**

| 항목 | 값 |
|---|---|
| 폼 필드명 | `files` |
| 최대 파일 크기 | 10MB |
| 최대 동시 업로드 수 | 5개 |
| 허용 MIME 타입 | `image/jpeg`, `image/png`, `image/gif`, `image/webp`, `image/svg+xml` |

description에 위 제한사항을 명시하고, `consumes`를 OpenAPI 3.0 `requestBody` + `content: { "multipart/form-data" }` 패턴으로 변경한다.

### 5.7 에러 응답 공통 패턴

모든 라우트에 공통 에러 응답 스키마를 일관되게 적용한다.

| 상태 코드 | 의미 | 적용 대상 |
|---|---|---|
| 400 | 요청 데이터 검증 실패 | body/query 파라미터가 있는 모든 라우트 |
| 401 | 인증 필요 (미로그인) | `requireAuth` 라우트 |
| 403 | 권한 없음 (Admin 아님) | `requireAdmin` 라우트 |
| 404 | 리소스 없음 | 단건 조회/수정/삭제 라우트 |
| 429 | Rate limit 초과 | rate limit이 설정된 라우트 |

```typescript
response: {
  200: SuccessSchema,
  400: ErrorResponseSchema,
  401: ErrorResponseSchema,
  403: ErrorResponseSchema,
  404: ErrorResponseSchema,
  429: ErrorResponseSchema,
},
```

### 5.8 프로덕션 Swagger UI 비활성화

`NODE_ENV === "production"`일 때 Swagger UI를 등록하지 않는다.

```typescript
const swaggerPlugin: FastifyPluginAsync = async (fastify) => {
  // OpenAPI 스펙 생성은 항상 등록 (내부 용도)
  await fastify.register(swagger, { ... });

  // Swagger UI는 프로덕션에서 비활성화
  if (env.NODE_ENV !== "production") {
    await fastify.register(swaggerUI, {
      routePrefix: "/docs",
      // ...
    });
    fastify.log.info("[Swagger] UI available at /docs");
  }
};
```

### 5.9 OpenAPI JSON 엔드포인트

`@fastify/swagger`가 자동으로 `/docs/json` (JSON)과 `/docs/yaml` (YAML)을 제공한다. 이 엔드포인트도 프로덕션에서는 Swagger UI와 함께 비활성화된다.

개발 환경에서 활용 가능한 용도:
- API 클라이언트 자동 생성
- 외부 문서화 도구 연동
- API 스펙 diff/변경 추적

## 6. API 연동

자기 자신에 대한 문서화. 외부 연동 없음.

## 7. 수용 기준

- [ ] 모든 Zod 스키마에 `.describe()`로 필드별 설명이 추가되었다
- [ ] Swagger UI "Try it out"에서 예시 데이터가 표시된다
- [ ] 22개 인증 라우트에 자물쇠 아이콘이 표시된다
- [ ] CSRF 필요 라우트의 description에 CSRF 안내가 포함된다
- [ ] Rate limit이 설정된 라우트의 description에 제한 정보가 표시된다
- [ ] 모든 리소스 태그가 상위에 정의되어 Swagger UI에서 올바르게 그룹핑된다
- [ ] 파일 업로드 엔드포인트가 OpenAPI 3.0 규격으로 문서화된다
- [ ] 에러 응답(400, 401, 403, 404, 429)이 일관되게 문서화된다
- [ ] `NODE_ENV=production`에서 Swagger UI(`/docs`)가 비활성화된다
- [ ] 개발 환경에서 `/docs/json`으로 OpenAPI 스펙을 다운로드할 수 있다

## 8. 에지 케이스

| 케이스 | 처리 |
|---|---|
| 프로덕션에서 `/docs` 접근 | 404 응답 (UI 미등록) |
| Zod `.transform()` 후 스키마 | transform 결과는 OpenAPI에 반영되지 않을 수 있음 - 응답 스키마에서 변환 후 타입 명시 |
| CSRF 토큰 만료 | description에 "세션 유지 시 유효" 명시 |
| rate limit 초과 | 429 응답 + `Retry-After` 헤더 (자동) |

## 9. 의존성

- 없음 (기반 기능)

## 10. 미해결 사항

없음. `.describe()` 중심으로 상세 설명을 제공하고, 필요한 예시는 현재 OpenAPI 변환 범위에서 관리한다.
