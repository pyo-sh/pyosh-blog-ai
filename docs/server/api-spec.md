# Server API 명세서

> Fastify 5 + Drizzle ORM | Base URL: `http://localhost:5500`

## 인증 방식

| 방식 | 설명 |
|---|---|
| **Admin Session** | `POST /api/auth/admin/login` 후 세션 쿠키 발급. `requireAdmin` 훅으로 보호 |
| **OAuth (Google/GitHub)** | Passport 기반. `request.user`로 접근. `requireAuth` 훅으로 보호 |
| **optionalAuth** | 인증 선택적. 비로그인 시에도 접근 가능 (게스트 댓글 등) |

---

## Auth (`/api/auth`)

| Method | Path | Auth | 설명 |
|---|---|---|---|
| GET | `/api/auth/google` | - | Google OAuth 리다이렉트 |
| GET | `/api/auth/google/callback` | - | Google OAuth 콜백 |
| GET | `/api/auth/github` | - | GitHub OAuth 리다이렉트 |
| GET | `/api/auth/github/callback` | - | GitHub OAuth 콜백 |
| POST | `/api/auth/admin/login` | - | 관리자 로그인 |
| POST | `/api/auth/admin/logout` | - | 관리자 로그아웃 (세션 파기) |
| GET | `/api/auth/me` | - | 현재 로그인 사용자 정보 |

### POST `/api/auth/admin/login`

**Request Body:**
```json
{ "email": "string", "password": "string (min 8)" }
```

**Response 200:**
```json
{ "admin": { "id": 1, "email": "...", "createdAt": "ISO", "updatedAt": "ISO", "lastLoginAt": "ISO" } }
```

### GET `/api/auth/me`

**Response 200 (Admin):**
```json
{ "type": "admin", "id": 1, "email": "...", "createdAt": "ISO", "updatedAt": "ISO", "lastLoginAt": "ISO" }
```

**Response 200 (OAuth):**
```json
{ "type": "oauth", "id": 1, "name": "...", "email": "...", "githubId": "...", "googleEmail": "..." }
```

---

## Posts

### Public (`/api/posts`)

| Method | Path | Auth | 설명 |
|---|---|---|---|
| GET | `/api/posts` | - | 게시글 목록 (공개+발행 글만) |
| GET | `/api/posts/:slug` | - | 게시글 상세 (slug 기반) |

#### GET `/api/posts`

**Query Parameters:**
| Param | Type | Default | 설명 |
|---|---|---|---|
| page | number | 1 | 페이지 번호 |
| limit | number (max 100) | 20 | 페이지당 개수 |
| categoryId | number | - | 카테고리 필터 |
| tagSlug | string | - | 태그 슬러그 필터 |
| sort | string | published_at | 정렬 기준 (`published_at` \| `created_at`) |
| order | string | desc | 정렬 방향 (`asc` \| `desc`) |

> Public API에서는 `status=published`, `visibility=public`, `includeDeleted=false`가 강제 적용됩니다.

**Response 200:**
```json
{
  "data": [PostDetail],
  "meta": { "page": 1, "limit": 20, "totalCount": 100, "totalPages": 5 }
}
```

#### GET `/api/posts/:slug`

**Response 200:**
```json
{
  "post": PostDetail,
  "prevPost": { "slug": "...", "title": "..." } | null,
  "nextPost": { "slug": "...", "title": "..." } | null
}
```

### Admin (`/api/admin/posts`) — `requireAdmin`

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/admin/posts` | 게시글 목록 (모든 상태/가시성, 삭제 포함 가능) |
| GET | `/api/admin/posts/:id` | 게시글 상세 (ID 기반) |
| POST | `/api/admin/posts` | 게시글 생성 |
| PATCH | `/api/admin/posts/:id` | 게시글 수정 |
| DELETE | `/api/admin/posts/:id` | 게시글 소프트 삭제 |
| PUT | `/api/admin/posts/:id/restore` | 삭제된 게시글 복원 |
| DELETE | `/api/admin/posts/:id/hard` | 게시글 하드 삭제 |

#### POST `/api/admin/posts`

**Request Body:**
```json
{
  "title": "string (max 200)",
  "contentMd": "string",
  "categoryId": 1,
  "thumbnailUrl": "/uploads/example.jpg", // optional (or https://...)
  "visibility": "public|private", // default: public
  "status": "draft|published|archived", // default: draft
  "tags": ["tag1", "tag2"],       // optional
  "publishedAt": "ISO datetime"   // optional
}
```

### PostDetail 스키마

```json
{
  "id": 1,
  "categoryId": 1,
  "title": "...",
  "slug": "...",
  "contentMd": "...",
  "thumbnailUrl": "/uploads/example.jpg",
  "visibility": "public",
  "status": "published",
  "publishedAt": "ISO",
  "createdAt": "ISO",
  "updatedAt": "ISO",
  "deletedAt": null,
  "category": { "id": 1, "name": "...", "slug": "..." },
  "tags": [{ "id": 1, "name": "...", "slug": "..." }],
}
```

---

## Categories (`/api/categories`)

| Method | Path | Auth | 설명 |
|---|---|---|---|
| GET | `/api/categories` | - | 카테고리 트리 (Cache: 300s) |
| POST | `/api/categories` | Admin | 카테고리 생성 |
| PATCH | `/api/categories/:id` | Admin | 카테고리 수정 |
| PATCH | `/api/categories/order` | Admin | 카테고리 순서 일괄 변경 |
| DELETE | `/api/categories/:id` | Admin | 카테고리 삭제 (자식/글 있으면 실패) |

#### GET `/api/categories`

**Query:** `?include_hidden=true` (관리자 세션일 때만 적용)

> 카테고리 조회는 트리 엔드포인트(`GET /api/categories`) 하나로 통합합니다.

**Response 200:**
```json
{
  "categories": [{
    "id": 1, "parentId": null, "name": "...", "slug": "...",
    "sortOrder": 0, "isVisible": true,
    "createdAt": "ISO", "updatedAt": "ISO",
    "children": [CategoryTree]
  }]
}
```

#### POST `/api/categories`

**Request Body:**
```json
{ "name": "string (max 50)", "parentId": 1, "isVisible": true }
```

#### PATCH `/api/categories/order`

**Request Body:**
```json
{ "items": [{ "id": 1, "sortOrder": 0 }, { "id": 2, "sortOrder": 1 }] }
```

---

## Assets (`/api/assets`)

| Method | Path | Auth | 설명 |
|---|---|---|---|
| POST | `/api/assets/upload` | Admin | 이미지 업로드 (multipart, max 5개, 10MB/개) |
| GET | `/api/assets/:id` | - | 에셋 정보 조회 |
| DELETE | `/api/assets/:id` | Admin | 에셋 삭제 (DB + 파일) |

#### POST `/api/assets/upload`

**Request:** `multipart/form-data` (허용 MIME: jpeg, png, gif, webp, svg)

**Response 201:**
```json
{ "assets": [{ "id": 1, "url": "/uploads/2026/02/uuid.png", "mimeType": "image/png", "sizeBytes": 12345, "width": 800, "height": 600 }] }
```

---

## Comments

### Public (`/api`)

| Method | Path | Auth | 설명 |
|---|---|---|---|
| GET | `/api/posts/:postId/comments` | optionalAuth | 댓글 목록 (계층형, 비밀글 마스킹) |
| POST | `/api/posts/:postId/comments` | optionalAuth | 댓글 작성 |
| DELETE | `/api/comments/:id` | optionalAuth | 댓글 삭제 (게스트: 비밀번호 필요) |

### Admin (`/api/admin`)

| Method | Path | Auth | 설명 |
|---|---|---|---|
| DELETE | `/api/admin/comments/:id` | Admin | 댓글 강제 삭제 |

#### POST `/api/posts/:postId/comments`

**OAuth 사용자:**
```json
{ "body": "string (max 2000)", "parentId": 1, "replyToCommentId": 1, "isSecret": false }
```

**게스트:**
```json
{ "body": "...", "parentId": 1, "replyToCommentId": 1, "isSecret": false,
  "guestName": "string (max 50)", "guestEmail": "string", "guestPassword": "string (min 4)" }
```

#### CommentDetail 스키마

```json
{
  "id": 1, "postId": 1, "parentId": null, "depth": 0,
  "body": "...", "isSecret": false, "status": "active",
  "author": { "type": "oauth|guest", "id": 1, "name": "...", "email": "...", "avatarUrl": "..." },
  "replyToName": null,
  "replies": [CommentDetail],
  "createdAt": "ISO", "updatedAt": "ISO"
}
```

> 대댓글은 최대 depth 1. `parentId`는 depth=0 댓글을 가리키고, `replyToCommentId`는 같은 parent 내 대상 댓글을 추적합니다.

---

## Guestbook

### Public (`/api`)

| Method | Path | Auth | 설명 |
|---|---|---|---|
| GET | `/api/guestbook` | optionalAuth | 방명록 목록 (페이지네이션) |
| POST | `/api/guestbook` | optionalAuth | 방명록 작성 |
| DELETE | `/api/guestbook/:id` | optionalAuth | 방명록 삭제 (게스트: 비밀번호 필요) |

### Admin (`/api/admin`)

| Method | Path | Auth | 설명 |
|---|---|---|---|
| DELETE | `/api/admin/guestbook/:id` | Admin | 방명록 강제 삭제 |

#### GET `/api/guestbook`

**Query:** `?page=1&limit=20` (max 100)

**Response 200:**
```json
{
  "data": [GuestbookEntryDetail],
  "meta": { "page": 1, "limit": 20, "totalCount": 50, "totalPages": 3 }
}
```

---

## Stats

### Public (`/api/stats`)

| Method | Path | Auth | 설명 |
|---|---|---|---|
| POST | `/api/stats/view` | - | 조회수 기록 (같은 IP 5분 내 중복 제거) |
| GET | `/api/stats/popular` | - | 인기 게시글 |

#### POST `/api/stats/view`

**Request Body:** `{ "postId": 1 }`

**Response 200:** `{ "success": true, "deduplicated": false }`

#### GET `/api/stats/popular`

**Query:** `?limit=10&days=7` (max limit=100, max days=365)

**Response 200:**
```json
{ "data": [{ "postId": 1, "slug": "...", "title": "...", "pageviews": 100, "uniques": 80 }] }
```

### Admin (`/api/admin/stats`)

| Method | Path | Auth | 설명 |
|---|---|---|---|
| GET | `/api/admin/stats/dashboard` | Admin | 대시보드 통계 |

**Response 200:**
```json
{ "todayPageviews": 50, "weekPageviews": 300, "monthPageviews": 1200, "totalPosts": 25, "totalComments": 150 }
```

---

## User (`/api/user`)

> 주의: 현재 인증 가드 미적용 (레거시)

| Method | Path | Auth | 설명 |
|---|---|---|---|
| GET | `/api/user/:id` | - | 사용자 정보 조회 |
| PUT | `/api/user/:id` | - | 사용자 정보 수정 |
| DELETE | `/api/user/:id` | - | 사용자 소프트 삭제 |

---

## SEO (root)

| Method | Path | 설명 |
|---|---|---|
| GET | `/sitemap.xml` | XML 사이트맵 (Cache: 3600s) |
| GET | `/rss.xml` | RSS 2.0 피드 - 최신 20개 공개 글 (Cache: 3600s) |

---

## Health Check

| Method | Path | 설명 |
|---|---|---|
| GET | `/health` | `{ "status": "ok", "timestamp": "ISO" }` |

---

## DB 스키마 요약 (13개 테이블)

| 테이블 | 용도 |
|---|---|
| `admin_tb` | 관리자 계정 (email + bcrypt) |
| `user_tb` | OAuth 사용자 (레거시) |
| `oauth_account_tb` | OAuth 계정 (provider별 관리) |
| `session_tb` | 세션 저장소 |
| `image_tb` | 이미지 (레거시) |
| `asset_tb` | 에셋 (현재 이미지 업로드 시스템) |
| `category_tb` | 카테고리 (트리 구조, self-FK) |
| `tag_tb` | 태그 |
| `post_tb` | 게시글 (소프트 삭제 지원) |
| `post_tag_tb` | 게시글-태그 M:N |
| `comment_tb` | 댓글 (계층형, 비밀글) |
| `guestbook_entry_tb` | 방명록 (계층형, 비밀글) |
| `stats_daily_tb` | 일별 조회 통계 |
