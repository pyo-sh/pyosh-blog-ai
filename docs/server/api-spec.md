# Server API Spec

> 기준: `server/src` 라우트/스키마/테스트 구현
>
> 서버: Fastify 5 + Zod + Drizzle ORM
>
> Base URL: `http://localhost:5500`

## 문서 기준

- 이 문서는 `docs/server/api-spec.md` 기존 내용이 아니라 현재 구현을 다시 읽고 정리한 버전이다.
- 입력/출력은 우선 `route` + `schema` 구현을 기준으로 작성했다.
- 동작 설명은 필요한 경우 테스트(`server/test/routes/*.test.ts`)로 교차 확인했다.

## 공통 규칙

### Swagger / OpenAPI

- 개발 환경에서는 Swagger UI가 `/docs`에 노출된다.
- OpenAPI 스펙은 서버가 등록한 Zod route schema에서 자동 생성된다.
- 루트 컬렉션 경로는 OpenAPI 상 `/api/posts/`, `/api/categories/`, `/api/assets/`처럼 trailing slash로 보일 수 있다. 이 문서에서는 읽기 편하게 slash 없는 형태로 표기했다.
- 카테고리 트리, 댓글 replies, 방명록 replies 같은 재귀 응답은 현재 OpenAPI 변환기 한계로 nested `items`가 느슨하게 표현될 수 있다. 그 구조 설명은 이 문서가 더 정확하다.

### 인증

| 방식 | 설명 |
|---|---|
| Admin session | `POST /api/auth/admin/login` 성공 시 세션 쿠키 발급. 관리자 전용 라우트는 `requireAdmin`으로 보호되며, 미인증 시 `403` |
| OAuth session | Google/GitHub Passport 로그인 후 `request.user` 사용. `/api/user/*`는 `requireAuth`로 보호되며, 미인증 시 `401` |
| Optional auth | 댓글/방명록 조회·작성·삭제 일부는 로그인 없이도 호출 가능 |

### CSRF

- `GET`, `HEAD`, `OPTIONS`, `TRACE` 외 메서드에 대해 `/api/admin/*` 전체에 CSRF 보호가 적용된다.
- Public 라우트 중 일부도 개별적으로 CSRF 보호를 적용한다.
- 토큰 발급: `GET /api/auth/csrf-token`
- 전송 헤더: `x-csrf-token`

### Rate limit

| Endpoint | Limit |
|---|---|
| `POST /api/auth/admin/login` | 5 req/min |
| `POST /api/posts/:postId/comments` | 10 req/min |
| `POST /api/guestbook` | 10 req/min |
| `POST /api/stats/view` | 30 req/min |

### 에러 응답

기본 형식:

```json
{
  "statusCode": 400,
  "error": "Bad Request",
  "message": "..."
}
```

검증 실패는 `details`가 추가될 수 있다.

```json
{
  "statusCode": 400,
  "error": "Validation Error",
  "message": "...",
  "details": []
}
```

## Health

| Method | Path | 설명 |
|---|---|---|
| GET | `/health` | 단순 헬스 체크 |
| GET | `/api/health/live` | liveness |
| GET | `/api/health/ready` | readiness + DB 상태 |
| GET | `/api/health` | 종합 상태 + DB 상태 |

### GET `/health`

```json
{ "status": "ok", "timestamp": "ISO-8601" }
```

### GET `/api/health/live`

```json
{
  "status": "ok",
  "timestamp": "ISO-8601",
  "uptime": 12345.67,
  "version": "string"
}
```

### GET `/api/health/ready`

```json
{
  "status": "ok | degraded | error",
  "timestamp": "ISO-8601",
  "uptime": 12345.67,
  "version": "string",
  "memory": {
    "rss": 0,
    "heapUsed": 0,
    "heapTotal": 0
  },
  "database": {
    "status": "ok | error",
    "latencyMs": 5
  }
}
```

### GET `/api/health`

```json
{
  "status": "ok | degraded | error",
  "timestamp": "ISO-8601",
  "uptime": 12345.67,
  "version": "string",
  "memory": {
    "rss": 0,
    "heapUsed": 0,
    "heapTotal": 0
  },
  "database": {
    "status": "ok | error",
    "latencyMs": 5
  }
}
```

## Auth

Prefix: `/api/auth`

| Method | Path | Auth | CSRF | 설명 |
|---|---|---|---|---|
| GET | `/google` | - | - | Google OAuth 시작. 환경변수 설정 시에만 등록 |
| GET | `/google/callback` | - | - | Google OAuth 콜백 |
| GET | `/github` | - | - | GitHub OAuth 시작. 환경변수 설정 시에만 등록 |
| GET | `/github/callback` | - | - | GitHub OAuth 콜백 |
| GET | `/csrf-token` | - | - | CSRF 토큰 발급 |
| POST | `/admin/login` | - | - | 관리자 로그인 |
| POST | `/admin/logout` | Admin session | Required | 관리자 로그아웃 |
| GET | `/me` | Optional | - | 현재 로그인 주체 조회 |

### GET `/api/auth/csrf-token`

```json
{ "token": "string" }
```

### POST `/api/auth/admin/login`

Request:

```json
{
  "username": "admin-user",
  "password": "password123"
}
```

제약:

- `username`: 4..100, 문자/숫자/`_`/`.`/`-` 허용
- 기존 legacy 계정 호환을 위해 이메일 형식도 허용
- `password`: 최소 8자

Response `200`:

```json
{
  "admin": {
    "id": 1,
    "username": "admin-user",
    "createdAt": "ISO-8601",
    "updatedAt": "ISO-8601",
    "lastLoginAt": "ISO-8601 | null"
  }
}
```

오류:

- `401`: 자격 증명 오류
- `429`: rate limit

### POST `/api/auth/admin/logout`

Response: `204 No Content`

### GET `/api/auth/me`

Admin 로그인 상태:

```json
{
  "type": "admin",
  "id": 1,
  "username": "admin-user",
  "createdAt": "ISO-8601",
  "updatedAt": "ISO-8601",
  "lastLoginAt": "ISO-8601 | null"
}
```

OAuth 로그인 상태:

```json
{
  "type": "oauth",
  "id": 1,
  "name": "User Name",
  "email": "user@example.com",
  "githubId": "12345",
  "googleEmail": "user@gmail.com"
}
```

오류:

- `401`: 로그인 필요

## Categories

Prefix: `/api/categories`

| Method | Path | Auth | CSRF | 설명 |
|---|---|---|---|---|
| GET | `/` | Public | - | 카테고리 트리 조회 |
| POST | `/` | Admin | Required | 카테고리 생성 |
| PATCH | `/tree` | Admin | Required | 카테고리 트리 일괄 변경 |
| PATCH | `/:id` | Admin | Required | 카테고리 수정 |
| DELETE | `/:id` | Admin | Required | 카테고리 삭제 |

### GET `/api/categories`

Query:

| Name | Type | Default | 설명 |
|---|---|---|---|
| `include_hidden` | `"true" \| "false"` | - | Admin session이 있을 때만 유효 |

응답:

```json
{
  "categories": [
    {
      "id": 1,
      "parentId": null,
      "name": "Backend",
      "slug": "backend",
      "sortOrder": 0,
      "isVisible": true,
      "publishedPostCount": 3,
      "totalPostCount": 5,
      "createdAt": "ISO-8601",
      "updatedAt": "ISO-8601",
      "children": []
    }
  ]
}
```

### POST `/api/categories`

Request:

```json
{
  "name": "Backend",
  "parentId": null,
  "isVisible": true
}
```

### PATCH `/api/categories/tree`

Request:

```json
{
  "changes": [
    { "id": 1, "parentId": null, "sortOrder": 0 },
    { "id": 2, "parentId": 1, "sortOrder": 1 }
  ]
}
```

Response:

```json
{ "success": true }
```

### PATCH `/api/categories/:id`

Request:

```json
{
  "name": "Renamed",
  "parentId": null,
  "sortOrder": 0,
  "isVisible": true
}
```

Response `200`:

```json
{
  "category": {
    "id": 1,
    "parentId": null,
    "name": "Renamed",
    "slug": "renamed",
    "sortOrder": 0,
    "isVisible": true,
    "publishedPostCount": 3,
    "totalPostCount": 5,
    "createdAt": "ISO-8601",
    "updatedAt": "ISO-8601"
  }
}
```

### DELETE `/api/categories/:id`

Query:

| Name | Type | 설명 |
|---|---|---|
| `action` | `move \| trash` | 삭제 방식 |
| `moveTo` | `number` | `action=move`일 때 필수 |

Response: `204 No Content`

## Assets

Prefix: `/api/assets`

| Method | Path | Auth | CSRF | 설명 |
|---|---|---|---|---|
| POST | `/upload` | Admin | Required | 이미지 업로드 |
| GET | `/` | Admin | - | 업로드된 에셋 목록 |
| GET | `/:id` | Public | - | 에셋 메타데이터 조회 |
| DELETE | `/bulk` | Admin | Required | 에셋 일괄 삭제 |
| DELETE | `/:id` | Admin | Required | 에셋 단건 삭제 |

### POST `/api/assets/upload`

Content-Type: `multipart/form-data`

폼 필드:

- `files`: 단일 또는 다중 파일

제약:

- 허용 MIME: `image/jpeg`, `image/png`, `image/gif`, `image/webp`, `image/svg+xml`
- 최대 파일 크기: 10MB
- 최대 파일 수: 5

Response `201`:

```json
{
  "assets": [
    {
      "id": 1,
      "url": "/uploads/example.webp",
      "mimeType": "image/webp",
      "sizeBytes": 12345,
      "width": 800,
      "height": 600
    }
  ]
}
```

### GET `/api/assets`

Query:

| Name | Type | Default |
|---|---|---|
| `page` | `number` | `1` |
| `limit` | `number` | `20` |

Response:

```json
{
  "data": [
    {
      "id": 1,
      "url": "/uploads/example.webp",
      "mimeType": "image/webp",
      "sizeBytes": 12345,
      "width": 800,
      "height": 600,
      "createdAt": "ISO-8601"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 1,
    "totalPages": 1
  }
}
```

### GET `/api/assets/:id`

```json
{
  "id": 1,
  "url": "/uploads/example.webp",
  "mimeType": "image/webp",
  "sizeBytes": 12345,
  "width": 800,
  "height": 600
}
```

### DELETE `/api/assets/bulk`

Request:

```json
{ "ids": [1, 2, 3] }
```

Response: `204 No Content`

## Posts

Public prefix: `/api/posts`

Admin prefix: `/api/admin/posts`

### Public endpoints

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/posts` | 공개 발행 게시글 목록 |
| GET | `/api/posts/slugs` | sitemap용 slug 목록 |
| GET | `/api/posts/:slug` | slug 기반 게시글 상세 |

### GET `/api/posts`

Query:

| Name | Type | Default | 설명 |
|---|---|---|---|
| `page` | `number` | `1` | 페이지 |
| `limit` | `number` | `10` | 최대 100 |
| `categoryId` | `number` | - | 카테고리 필터 |
| `tagSlug` | `string` | - | 태그 슬러그 |
| `q` | `string` | - | 검색어 |
| `filter` | `title_content \| title \| content \| tag \| category \| comment` | `title_content` | 검색 대상 |
| `sort` | `published_at \| created_at` | `published_at` | 정렬 기준 |
| `order` | `asc \| desc` | `desc` | 정렬 방향 |

강제 조건:

- `status=published`
- `visibility=public`
- `includeDeleted=false`

Response:

```json
{
  "data": [
    {
      "id": 1,
      "categoryId": 1,
      "title": "Post title",
      "slug": "post-title",
      "summary": "summary",
      "description": "description",
      "thumbnailUrl": "/uploads/thumb.webp",
      "visibility": "public",
      "status": "published",
      "commentStatus": "open",
      "isPinned": false,
      "publishedAt": "ISO-8601 | null",
      "contentModifiedAt": "ISO-8601 | null",
      "createdAt": "ISO-8601",
      "updatedAt": "ISO-8601",
      "deletedAt": null,
      "tags": [
        { "id": 1, "name": "fastify", "slug": "fastify" }
      ],
      "totalPageviews": 10,
      "commentCount": 2,
      "category": {
        "id": 1,
        "name": "Backend",
        "slug": "backend"
      }
    }
  ],
  "meta": {
    "page": 1,
    "limit": 10,
    "total": 1,
    "totalPages": 1
  }
}
```

### GET `/api/posts/slugs`

```json
{
  "slugs": [
    {
      "slug": "post-title",
      "updatedAt": "ISO-8601"
    }
  ]
}
```

### GET `/api/posts/:slug`

```json
{
  "post": {
    "id": 1,
    "categoryId": 1,
    "title": "Post title",
    "slug": "post-title",
    "contentMd": "# Markdown",
    "summary": "summary",
    "description": "description",
    "thumbnailUrl": "/uploads/thumb.webp",
    "visibility": "public",
    "status": "published",
    "commentStatus": "open",
    "isPinned": false,
    "publishedAt": "ISO-8601 | null",
    "contentModifiedAt": "ISO-8601 | null",
    "createdAt": "ISO-8601",
    "updatedAt": "ISO-8601",
    "deletedAt": null,
    "tags": [],
    "totalPageviews": 10,
    "commentCount": 2,
    "category": {
      "id": 1,
      "name": "Backend",
      "slug": "backend",
      "ancestors": [
        { "name": "Root", "slug": "root" }
      ]
    }
  },
  "prevPost": { "slug": "prev-post", "title": "Prev" },
  "nextPost": { "slug": "next-post", "title": "Next" }
}
```

### Admin endpoints

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/admin/posts` | 전체 게시글 목록 |
| GET | `/api/admin/posts/pinned-count` | pinned 게시글 수 |
| GET | `/api/admin/posts/:id` | ID 기반 상세 |
| POST | `/api/admin/posts` | 게시글 생성 |
| PATCH | `/api/admin/posts/bulk` | 벌크 작업 |
| PATCH | `/api/admin/posts/:id` | 게시글 수정 |
| DELETE | `/api/admin/posts/:id` | soft delete |
| PUT | `/api/admin/posts/:id/restore` | 복원 |
| DELETE | `/api/admin/posts/:id/hard` | hard delete |

### GET `/api/admin/posts`

Query:

| Name | Type | Default | 설명 |
|---|---|---|---|
| `page` | `number` | `1` | 페이지 |
| `limit` | `number` | `20` | 최대 100 |
| `categoryId` | `number` | - | 카테고리 필터 |
| `tagSlug` | `string` | - | 태그 슬러그 |
| `q` | `string` | - | 검색어 |
| `status` | `draft \| published \| archived` | - | 상태 필터 |
| `visibility` | `public \| private` | - | 공개 범위 |
| `sort` | `published_at \| created_at \| totalPageviews \| commentCount` | `created_at` | 정렬 기준 |
| `order` | `asc \| desc` | `desc` | 정렬 방향 |
| `includeDeleted` | `boolean` | `false` | soft delete 포함 여부 |

응답 구조는 public 목록과 동일하다.

### GET `/api/admin/posts/pinned-count`

```json
{ "pinnedCount": 3 }
```

### POST `/api/admin/posts`

Request:

```json
{
  "title": "My First Post",
  "contentMd": "# Hello",
  "categoryId": 1,
  "summary": "summary",
  "description": "description",
  "thumbnailUrl": "/uploads/example.webp",
  "visibility": "public",
  "status": "draft",
  "commentStatus": "open",
  "isPinned": false,
  "tags": ["fastify", "zod"],
  "publishedAt": "2026-04-04T12:00:00.000Z"
}
```

주요 제약:

- `title`: 1..200
- `contentMd`: 1자 이상
- `summary`: 1..200, optional
- `description`: 1..300, optional
- `thumbnailUrl`: `null`, 빈 문자열, `/uploads/...`, `http://`, `https://` 허용
- `status`: `draft | published | archived`
- `visibility`: `public | private`
- `commentStatus`: `open | locked | disabled`
- `isPinned`: optional, default `false`
- `tags[]`: 각 1..30
- `publishedAt`: ISO datetime

구현 메모:

- 제목에서 slug를 자동 생성한다.
- 중복 slug는 suffix를 붙여 고유화한다.
- `status=published`이고 `publishedAt`이 없으면 자동 설정된다.
- pinned 게시글은 최대 5개까지 허용되며 초과 시 `409`.

Response `201`:

```json
{ "post": { "...PostDetail" : "GET /api/posts/:slug 의 post와 동일 구조" } }
```

### PATCH `/api/admin/posts/bulk`

Request:

```json
{
  "ids": [1, 2, 3],
  "action": "update",
  "categoryId": 2,
  "commentStatus": "locked"
}
```

`action`:

- `update`
- `soft_delete`
- `restore`
- `hard_delete`

규칙:

- `action=update`일 때 `categoryId` 또는 `commentStatus` 중 하나 이상 필요
- 그 외 action에서는 `categoryId`, `commentStatus`를 보내면 검증 실패

Response: `204 No Content`

### PATCH `/api/admin/posts/:id`

수정 가능한 필드:

- `title`
- `contentMd`
- `categoryId`
- `summary`
- `description`
- `thumbnailUrl`
- `visibility`
- `status`
- `commentStatus`
- `isPinned`
- `tags`
- `publishedAt`

응답은 `PostDetail` 래핑 형식:

```json
{ "post": { "...PostDetail": "..." } }
```

### DELETE `/api/admin/posts/:id`

Response: `204 No Content`

### PUT `/api/admin/posts/:id/restore`

Response:

```json
{ "post": { "...PostDetail": "..." } }
```

### DELETE `/api/admin/posts/:id/hard`

Response: `204 No Content`

## Tags

Prefix: `/api/tags`

| Method | Path | 설명 |
|---|---|---|
| GET | `/` | 공개 발행 게시글 기준 태그 목록 |

### GET `/api/tags`

```json
{
  "tags": [
    {
      "id": 1,
      "name": "fastify",
      "slug": "fastify",
      "postCount": 3
    }
  ]
}
```

## Comments

Public prefix: `/api`

Admin prefix: `/api/admin`

### Public endpoints

| Method | Path | Auth | CSRF | 설명 |
|---|---|---|---|---|
| GET | `/posts/:postId/comments` | Optional | - | 게시글 댓글 조회 |
| POST | `/posts/:postId/comments` | Optional | Required | 댓글 작성 |
| POST | `/comments/:id/reveal` | - | - | 비밀 댓글 복원 토큰 조회 |
| DELETE | `/comments/:id` | Optional | Required | 댓글 삭제 |

### GET `/api/posts/:postId/comments`

Query:

| Name | Type | Default | 설명 |
|---|---|---|---|
| `page` | `number` | `1` | 루트 댓글 페이지 |
| `limit` | `number` | `10` | 최대 50 |

Response:

```json
{
  "data": [
    {
      "id": 1,
      "postId": 10,
      "parentId": null,
      "depth": 0,
      "body": "댓글 본문",
      "isSecret": false,
      "status": "active",
      "author": {
        "type": "guest",
        "name": "홍길동",
        "email": "guest@example.com"
      },
      "replyToName": null,
      "replies": [],
      "createdAt": "ISO-8601",
      "updatedAt": "ISO-8601"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 10,
    "totalCount": 1,
    "totalRootComments": 1,
    "totalPages": 1
  }
}
```

메모:

- 응답은 계층 구조다.
- 페이지네이션은 루트 댓글 기준이다.
- 공개 응답의 `status`는 `active | deleted`.
- 비밀 댓글은 작성자와 관리자만 원문을 볼 수 있다.

### POST `/api/posts/:postId/comments`

OAuth 작성:

```json
{
  "body": "댓글",
  "parentId": 1,
  "replyToCommentId": 2,
  "isSecret": false
}
```

Guest 작성:

```json
{
  "body": "댓글",
  "parentId": 1,
  "replyToCommentId": 2,
  "isSecret": true,
  "guestName": "홍길동",
  "guestEmail": "guest@example.com",
  "guestPassword": "pass1234"
}
```

제약:

- `body`: 1..2000
- `guestName`: 1..50
- `guestEmail`: optional
- `guestPassword`: 4..100

구현 메모:

- depth 2 이상 대댓글은 허용되지 않는다.
- 게스트 비밀 댓글 작성 시 `revealToken`이 발급된다.

Response `201`:

```json
{
  "data": {
    "id": 1,
    "postId": 10,
    "parentId": null,
    "depth": 0,
    "body": "댓글",
    "isSecret": true,
    "status": "active",
    "author": {
      "type": "guest",
      "name": "홍길동",
      "email": "guest@example.com"
    },
    "replyToName": null,
    "replies": [],
    "createdAt": "ISO-8601",
    "updatedAt": "ISO-8601"
  },
  "revealToken": "string | null"
}
```

### POST `/api/comments/:id/reveal`

Request:

```json
{ "revealToken": "token-string" }
```

Response:

```json
{
  "data": {
    "id": 1,
    "postId": 10,
    "parentId": null,
    "depth": 0,
    "body": "원문",
    "isSecret": true,
    "status": "active",
    "author": {
      "type": "guest",
      "name": "홍길동"
    },
    "replyToName": null,
    "replies": [],
    "createdAt": "ISO-8601",
    "updatedAt": "ISO-8601"
  }
}
```

### DELETE `/api/comments/:id`

OAuth 사용자는 세션으로 삭제 가능.

게스트는 body에 비밀번호 전달:

```json
{ "guestPassword": "pass1234" }
```

Response: `204 No Content`

### Admin endpoints

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/admin/comments` | 전체 댓글 목록 |
| GET | `/api/admin/comments/:id/thread` | 부모 + 답글 전체 |
| PUT | `/api/admin/comments/:id/restore` | `deleted` 또는 `hidden` 복원 |
| DELETE | `/api/admin/comments/bulk` | 벌크 복원/삭제 |
| DELETE | `/api/admin/comments/:id` | 단건 soft/hard delete |

### GET `/api/admin/comments`

Query:

| Name | Type | Default |
|---|---|---|
| `page` | `number` | `1` |
| `limit` | `number` | `20` |
| `postId` | `number` | - |
| `status` | `active \| deleted \| hidden` | - |
| `authorType` | `oauth \| guest` | - |
| `startDate` | `string` | - |
| `endDate` | `string` | - |
| `sort` | `created_at` | `created_at` |
| `order` | `asc \| desc` | `desc` |

Response:

```json
{
  "data": [
    {
      "id": 1,
      "postId": 10,
      "parentId": null,
      "depth": 0,
      "body": "관리자용 원문",
      "isSecret": true,
      "status": "hidden",
      "author": {
        "type": "oauth",
        "id": 3,
        "name": "OAuth User",
        "avatarUrl": "https://..."
      },
      "replyToName": null,
      "post": {
        "id": 10,
        "title": "Post title"
      },
      "createdAt": "ISO-8601",
      "updatedAt": "ISO-8601"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 1,
    "totalPages": 1
  }
}
```

### GET `/api/admin/comments/:id/thread`

```json
{
  "parent": { "...AdminCommentItem": "..." },
  "replies": [{ "...AdminCommentItem": "..." }]
}
```

### PUT `/api/admin/comments/:id/restore`

```json
{ "success": true }
```

### DELETE `/api/admin/comments/bulk`

Request:

```json
{
  "ids": [1, 2, 3],
  "action": "restore"
}
```

`action`:

- `restore`
- `soft_delete`
- `hard_delete`

Response: `204 No Content`

### DELETE `/api/admin/comments/:id`

Query:

| Name | Type | Default |
|---|---|---|
| `action` | `soft_delete \| hard_delete` | `soft_delete` |

Response: `204 No Content`

## Guestbook

Public prefix: `/api`

Admin prefix: `/api/admin`

### Public endpoints

| Method | Path | Auth | CSRF | 설명 |
|---|---|---|---|---|
| GET | `/guestbook` | Optional | - | 방명록 목록 |
| POST | `/guestbook` | Optional | Required | 방명록 작성 |
| DELETE | `/guestbook/:id` | Optional | Required | 방명록 삭제 |

### GET `/api/guestbook`

Query:

| Name | Type | Default |
|---|---|---|
| `page` | `number` | `1` |
| `limit` | `number` | `20` |

Response:

```json
{
  "data": [
    {
      "id": 1,
      "parentId": null,
      "body": "방명록 본문",
      "isSecret": false,
      "status": "active",
      "author": {
        "type": "guest",
        "name": "방문자",
        "email": "visitor@example.com"
      },
      "replies": [],
      "createdAt": "ISO-8601",
      "updatedAt": "ISO-8601"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 1,
    "totalPages": 1
  }
}
```

메모:

- 응답은 계층 구조다.
- 공개 응답의 `status`는 `active | deleted`.
- 비밀글은 작성자와 관리자만 원문을 볼 수 있다.

### POST `/api/guestbook`

OAuth 작성:

```json
{
  "body": "OAuth 방명록",
  "parentId": 1,
  "isSecret": false
}
```

Guest 작성:

```json
{
  "body": "게스트 방명록",
  "parentId": 1,
  "isSecret": false,
  "guestName": "방문자",
  "guestEmail": "visitor@example.com",
  "guestPassword": "pass1234"
}
```

제약:

- `body`: 1..2000
- `guestName`: 1..50
- `guestEmail`: 필수
- `guestPassword`: 4..100

구현 메모:

- 방명록 기능이 비활성화되어 있으면 `403`

Response `201`:

```json
{
  "data": {
    "id": 1,
    "parentId": null,
    "body": "방명록 본문",
    "isSecret": false,
    "status": "active",
    "author": {
      "type": "guest",
      "name": "방문자",
      "email": "visitor@example.com"
    },
    "replies": [],
    "createdAt": "ISO-8601",
    "updatedAt": "ISO-8601"
  }
}
```

### DELETE `/api/guestbook/:id`

게스트 삭제 요청:

```json
{ "guestPassword": "pass1234" }
```

Response: `204 No Content`

### Admin endpoints

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/admin/guestbook` | 전체 방명록 목록 |
| DELETE | `/api/admin/guestbook/bulk` | 벌크 비가역 삭제 |
| PATCH | `/api/admin/guestbook/bulk` | 벌크 hide/restore |
| PATCH | `/api/admin/guestbook/:id` | 단건 hide/restore |
| DELETE | `/api/admin/guestbook/:id` | 단건 soft/hard delete |

### GET `/api/admin/guestbook`

Query:

| Name | Type | Default |
|---|---|---|
| `page` | `number` | `1` |
| `limit` | `number` | `20` |
| `status` | `active \| deleted \| hidden` | - |
| `authorType` | `oauth \| guest` | - |
| `q` | `string` | - |
| `startDate` | `string` | - |
| `endDate` | `string` | - |

Response:

```json
{
  "data": [
    {
      "id": 1,
      "parentId": null,
      "body": "관리자용 원문",
      "isSecret": true,
      "status": "hidden",
      "author": {
        "type": "guest",
        "name": "방문자",
        "email": "visitor@example.com"
      },
      "createdAt": "ISO-8601",
      "updatedAt": "ISO-8601"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 1,
    "totalPages": 1
  }
}
```

### DELETE `/api/admin/guestbook/bulk`

Request:

```json
{
  "ids": [1, 2, 3],
  "action": "soft_delete"
}
```

`action`:

- `soft_delete`
- `hard_delete`

Response: `204 No Content`

### PATCH `/api/admin/guestbook/bulk`

Request:

```json
{
  "ids": [1, 2, 3],
  "action": "hide"
}
```

`action`:

- `hide`
- `restore`

Response: `204 No Content`

### PATCH `/api/admin/guestbook/:id`

Query:

| Name | Type |
|---|---|
| `action` | `hide \| restore` |

Response: `204 No Content`

### DELETE `/api/admin/guestbook/:id`

Query:

| Name | Type |
|---|---|
| `action` | `soft_delete \| hard_delete` |

Response: `204 No Content`

## Settings

Public prefix: `/api/settings`

Admin prefix: `/api/admin`

| Method | Path | Auth | CSRF | 설명 |
|---|---|---|---|---|
| GET | `/api/settings/guestbook` | Public | - | 방명록 활성 상태 조회 |
| PATCH | `/api/admin/settings/guestbook` | Admin | Required | 방명록 활성 상태 변경 |

### GET `/api/settings/guestbook`

```json
{ "enabled": true }
```

### PATCH `/api/admin/settings/guestbook`

Request:

```json
{ "enabled": false }
```

Response:

```json
{ "enabled": false }
```

## Stats

Public prefix: `/api/stats`

Admin prefix: `/api/admin/stats`

| Method | Path | Auth | CSRF | 설명 |
|---|---|---|---|---|
| POST | `/api/stats/view` | Public | Required | 조회수 기록 |
| GET | `/api/stats/popular` | Public | - | 인기 게시글 |
| GET | `/api/stats/total-views` | Public | - | 사이트 전체 조회수 |
| GET | `/api/admin/stats/dashboard` | Admin | - | 대시보드 통계 |

### POST `/api/stats/view`

Request:

```json
{ "postId": 1 }
```

또는 사이트 전체 조회수:

```json
{}
```

Response:

```json
{
  "success": true,
  "deduplicated": false
}
```

메모:

- 동일 IP가 같은 대상에 5분 내 재요청하면 `deduplicated: true`
- `postId`가 존재하면 공개 발행 게시글에 대해서만 집계되며, 그 외는 `404`

### GET `/api/stats/popular`

Query:

| Name | Type | Default | 설명 |
|---|---|---|---|
| `limit` | `number` | `10` | 최대 100 |
| `days` | `number` | `7` | 최대 365 |

Response:

```json
{
  "data": [
    {
      "postId": 1,
      "slug": "post-title",
      "title": "Post title",
      "pageviews": 10,
      "uniques": 8
    }
  ]
}
```

### GET `/api/stats/total-views`

```json
{ "totalPageviews": 1234 }
```

### GET `/api/admin/stats/dashboard`

```json
{
  "todayPageviews": 10,
  "weekPageviews": 70,
  "monthPageviews": 300,
  "totalPosts": 12,
  "totalComments": 40,
  "postsByStatus": {
    "draft": 2,
    "published": 8,
    "archived": 2
  }
}
```

## User

Prefix: `/api/user`

모든 엔드포인트는 OAuth 로그인 필요.

| Method | Path | 설명 |
|---|---|---|
| GET | `/me` | 내 프로필 조회 |
| PUT | `/me` | 내 프로필 수정 |
| DELETE | `/me` | 회원 탈퇴 |

### GET `/api/user/me`

```json
{
  "id": 1,
  "provider": "github",
  "email": "user@example.com",
  "displayName": "User Name",
  "avatarUrl": "https://example.com/avatar.png",
  "createdAt": "ISO-8601",
  "updatedAt": "ISO-8601"
}
```

메모:

- `providerUserId`, `deletedAt` 등 민감 필드는 노출하지 않는다.

### PUT `/api/user/me`

Request:

```json
{
  "displayName": "New Name",
  "avatarUrl": null
}
```

제약:

- `displayName`: 1..100
- `avatarUrl`: 유효한 URL 또는 `null`
- 빈 body도 허용되며 no-op으로 처리된다

Response는 `GET /api/user/me`와 동일 구조다.

### DELETE `/api/user/me`

Response: `204 No Content`

구현 메모:

- 계정은 soft delete 처리된다.
- 세션도 함께 파기된다.
- 탈퇴한 사용자의 댓글/방명록 작성자명은 별도 마스킹 규칙을 따른다.

## SEO

루트 경로에 등록된다.

| Method | Path | 설명 |
|---|---|---|
| GET | `/sitemap.xml` | sitemap XML |
| GET | `/rss.xml` | RSS 2.0 XML |

### GET `/sitemap.xml`

- 공개 정적 페이지(` /`, `/portfolio`, `/guestbook`)
- 공개 카테고리
- 공개 발행 게시글

응답 헤더:

- `Content-Type: application/xml; charset=utf-8`
- `Cache-Control: public, max-age=3600`

### GET `/rss.xml`

- 최신 공개 발행 게시글 최대 20개
- 본문 Markdown을 평문화 후 220자 기준으로 description 생성

응답 헤더:

- `Content-Type: application/rss+xml; charset=utf-8`
- `Cache-Control: public, max-age=3600`
