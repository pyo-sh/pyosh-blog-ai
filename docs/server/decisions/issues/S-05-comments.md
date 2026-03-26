# Comments API

> 댓글 공개/관리자 엔드포인트 8개 구현 (계층형, 게스트/OAuth, 비밀글, 소프트/하드 삭제)

## SPEC 참조

- `docs/server/api-spec.md` > Comments (Public + Admin), CommentDetail 스키마, CSRF 보호, Rate limiting

## 상세

### Public 엔드포인트 (`/api`)

| Method | Path | Auth | 설명 |
|---|---|---|---|
| GET | `/api/posts/:postId/comments` | optionalAuth | 댓글 목록 (계층형, 비밀글 마스킹) |
| POST | `/api/posts/:postId/comments` | optionalAuth, CSRF | 댓글 작성 (10 req/min) |
| DELETE | `/api/comments/:id` | optionalAuth, CSRF | 댓글 소프트 삭제 (게스트: 비밀번호 필요) |

### Admin 엔드포인트 (`/api/admin`)

| Method | Path | Auth | 설명 |
|---|---|---|---|
| GET | `/api/admin/comments` | Admin | 댓글 목록 (필터 + 페이지네이션, post.title 포함) |
| GET | `/api/admin/comments/:id/thread` | Admin | 스레드 조회 (부모 + 모든 답글) |
| PUT | `/api/admin/comments/:id/restore` | Admin | 댓글 복원 (deleted -> active) |
| DELETE | `/api/admin/comments/:id` | Admin | 댓글 삭제 (`?action=soft_delete` \| `?action=hard_delete`) |
| DELETE | `/api/admin/comments/bulk` | Admin | 댓글 벌크 삭제/복원 |

#### GET `/api/posts/:postId/comments`

**Query Parameters:**

| Param | Type | Default | 설명 |
|---|---|---|---|
| page | number | 1 | 페이지 번호 (루트 댓글 기준) |
| limit | number (max 50) | 10 | 페이지당 루트 댓글 수 |

**Response 200:**
```json
{
  "data": [CommentDetail],
  "meta": { "page": 1, "limit": 10, "totalCount": 50, "totalRootComments": 30, "totalPages": 3 }
}
```

#### POST `/api/posts/:postId/comments`

**OAuth 사용자:**
```json
{ "body": "string (1-2000)", "parentId": 1, "replyToCommentId": 1, "isSecret": false }
```

**게스트:**
```json
{ "body": "...", "parentId": 1, "replyToCommentId": 1, "isSecret": false,
  "guestName": "string (1-50)", "guestEmail": "string (email)", "guestPassword": "string (4-100)" }
```

- CSRF 토큰 필요
- Rate limit: 10 req/min

#### DELETE `/api/comments/:id`

**Body (게스트만):**
```json
{ "guestPassword": "string (min 4)" }
```

- CSRF 토큰 필요
- 소프트 삭제 (body 보존, status/deletedAt만 변경)
- 게스트는 비밀번호 확인 필요

#### GET `/api/admin/comments`

**Query Parameters:**

| Param | Type | Default | 설명 |
|---|---|---|---|
| page | number | 1 | 페이지 번호 |
| limit | number (max 100) | 20 | 페이지당 개수 |
| status | string | - | 상태 필터 (`active` \| `deleted` \| `hidden`) |
| authorType | string | - | 작성자 유형 (`oauth` \| `guest`) |
| postId | number | - | 특정 글의 댓글만 |
| startDate | string | - | 시작일 (YYYY-MM-DD) |
| endDate | string | - | 종료일 (YYYY-MM-DD) |
| sort | string | created_at | 정렬 기준 (`created_at`) |
| order | string | desc | 정렬 방향 (`asc` \| `desc`) |

**Response 200:**
```json
{
  "data": [{ ...CommentDetail, "post": { "id": 1, "title": "..." } }],
  "meta": { "page": 1, "limit": 20, "totalCount": 100, "totalPages": 5 }
}
```

#### GET `/api/admin/comments/:id/thread`

**Response 200:**
```json
{
  "parent": CommentDetail,
  "replies": [CommentDetail]
}
```

#### PUT `/api/admin/comments/:id/restore`

**Response 200:**
```json
{ "success": true }
```

- `status: "deleted"` -> `status: "active"`, `deletedAt: null`

#### DELETE `/api/admin/comments/:id`

**Query:** `?action=soft_delete` 또는 `?action=hard_delete`

- `soft_delete`: body 보존, status/deletedAt만 변경
- `hard_delete`: DB에서 완전 삭제

#### DELETE `/api/admin/comments/bulk`

**Request Body:**
```json
{ "ids": [1, 2, 3], "action": "restore | soft_delete | hard_delete" }
```

- `restore`: deleted -> active 복원
- `soft_delete`: body 보존, status/deletedAt만 변경
- `hard_delete`: 대댓글 cascade 삭제

### CommentDetail 스키마

```json
{
  "id": 1, "postId": 1, "parentId": null, "depth": 0,
  "body": "...", "isSecret": false, "status": "active",
  "author": { "type": "oauth | guest", "id": 1, "name": "...", "email": "...", "avatarUrl": "..." },
  "replyToName": null,
  "replies": [CommentDetail],
  "createdAt": "ISO", "updatedAt": "ISO"
}
```

### 댓글 구조 규칙

- 대댓글은 최대 depth 1
- `parentId`는 depth=0 댓글을 가리킨다
- `replyToCommentId`는 같은 parent 내 대상 댓글을 추적한다
- 비밀글(`isSecret: true`)은 작성자/관리자 외에는 body가 마스킹된다

## 수용 기준

- [ ] GET `/api/posts/:postId/comments`가 계층형 댓글 목록을 반환한다
- [ ] 페이지네이션이 루트 댓글 기준으로 동작한다 (대댓글은 루트와 함께 반환)
- [ ] 비밀글이 작성자/관리자 외에는 body가 마스킹된다
- [ ] POST `/api/posts/:postId/comments`가 게스트/OAuth 댓글을 생성한다
- [ ] 댓글 작성 시 CSRF 토큰이 검증된다
- [ ] 댓글 작성에 10 req/min rate limit이 적용된다
- [ ] 게스트 댓글에 guestName, guestEmail, guestPassword가 필요하다
- [ ] 게스트 비밀번호가 해시되어 저장된다
- [ ] DELETE `/api/comments/:id`가 게스트 비밀번호를 확인 후 소프트 삭제한다
- [ ] 댓글 삭제 시 CSRF 토큰이 검증된다
- [ ] Admin GET `/api/admin/comments`가 필터/페이지네이션/post.title을 지원한다
- [ ] Admin GET `/api/admin/comments/:id/thread`가 부모 + 답글을 반환한다
- [ ] Admin PUT `/api/admin/comments/:id/restore`가 deleted -> active 복원한다
- [ ] Admin DELETE가 soft_delete/hard_delete action을 지원한다
- [ ] Admin 벌크 삭제가 restore/soft_delete/hard_delete를 지원한다
- [ ] 대댓글 depth가 최대 1로 제한된다

## 의존성

- Blocked by: S-03, S-04
- Blocks: 없음

## 참고

- 소프트 삭제는 body를 보존하고 status/deletedAt만 변경한다. 하드 삭제는 DB에서 완전히 제거하며, 대댓글도 cascade 삭제된다.
- 게스트 비밀번호는 반드시 해시하여 저장한다 (argon2 또는 bcrypt).
- 비밀글 마스킹은 Public API에서만 적용된다. Admin API에서는 모든 댓글의 body를 확인할 수 있다.
