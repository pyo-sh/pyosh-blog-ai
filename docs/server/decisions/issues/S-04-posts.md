# Posts API

> 게시글 공개/관리자 엔드포인트 11개 구현 (목록, 상세, CRUD, 벌크, 소프트/하드 삭제)

## SPEC 참조

- `docs/server/api-spec.md` > Posts (Public + Admin), PostDetail 스키마, PostListItem 스키마

## 상세

### Public 엔드포인트 (`/api/posts`)

| Method | Path | Auth | 설명 |
|---|---|---|---|
| GET | `/api/posts` | - | 게시글 목록 (공개+발행 글만) |
| GET | `/api/posts/slugs` | - | 발행된 글 slug 목록 (sitemap용) |
| GET | `/api/posts/:slug` | - | 게시글 상세 (slug 기반) |

#### GET `/api/posts`

**Query parameters:**

| Param | Type | Default | 설명 |
|---|---|---|---|
| page | number | 1 | 페이지 번호 |
| limit | number (1-100) | 10 | 페이지당 개수 |
| categoryId | number | - | 카테고리 필터 |
| tagSlug | string | - | 태그 슬러그 필터 |
| q | string | - | 제목/내용 검색 |
| filter | string | title_content | 검색 범위 (`title_content` \| `title` \| `content` \| `tag` \| `category` \| `comment`) |
| sort | string | published_at | 정렬 기준 (`published_at` \| `created_at`) |
| order | string | desc | 정렬 방향 (`asc` \| `desc`) |

> Public API에서는 `status=published`, `visibility=public`, `deletedAt IS NULL`이 강제 적용됩니다.

**Response 200:**
```json
{
  "data": [PostListItem],
  "meta": { "page": 1, "limit": 20, "totalCount": 100, "totalPages": 5 }
}
```

#### GET `/api/posts/slugs`

발행된 글의 slug + updatedAt만 반환하는 경량 엔드포인트 (sitemap용).

**Response 200:**
```json
{ "slugs": [{ "slug": "...", "updatedAt": "ISO" }] }
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

### Admin 엔드포인트 (`/api/admin/posts`) - requireAdmin

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/admin/posts` | 게시글 목록 (모든 상태/가시성, 삭제 포함 가능) |
| GET | `/api/admin/posts/:id` | 게시글 상세 (ID 기반) |
| POST | `/api/admin/posts` | 게시글 생성 |
| PATCH | `/api/admin/posts/:id` | 게시글 수정 |
| PATCH | `/api/admin/posts/bulk` | 게시글 벌크 작업 |
| DELETE | `/api/admin/posts/:id` | 게시글 소프트 삭제 |
| PUT | `/api/admin/posts/:id/restore` | 삭제된 게시글 복원 |
| DELETE | `/api/admin/posts/:id/hard` | 게시글 하드 삭제 |

#### GET `/api/admin/posts`

**Query Parameters:**

| Param | Type | Default | 설명 |
|---|---|---|---|
| page | number | 1 | 페이지 번호 |
| limit | number (max 100) | 20 | 페이지당 개수 |
| status | string | - | 상태 필터 (`draft` \| `published` \| `archived`) |
| visibility | string | - | 공개여부 필터 (`public` \| `private`) |
| q | string | - | 제목/내용 검색 |
| sort | string | created_at | 정렬 기준 (`created_at` \| `published_at` \| `totalPageviews` \| `commentCount`) |
| order | string | desc | 정렬 방향 (`asc` \| `desc`) |
| includeDeleted | boolean | false | 삭제된 글 포함 |

#### POST `/api/admin/posts`

**Request Body:**
```json
{
  "title": "string (1-200)",
  "contentMd": "string (min 1)",
  "categoryId": 1,
  "thumbnailUrl": "/uploads/example.jpg",
  "visibility": "public | private",
  "status": "draft | published | archived",
  "tags": ["tag1", "tag2"],
  "publishedAt": "ISO datetime",
  "summary": "string (max 200)",
  "description": "string (max 300)",
  "commentStatus": "open | locked | disabled"
}
```

**Response 201:** `{ "post": PostDetail }`

#### PATCH `/api/admin/posts/bulk`

**Request Body:**
```json
{
  "ids": [1, 2, 3],
  "action": "update | soft_delete | restore | hard_delete",
  "categoryId": 1,
  "commentStatus": "open | locked | disabled"
}
```

- `update`: `categoryId`, `commentStatus` 중 하나 이상 필수
- 단일 트랜잭션: 전체 성공 or 전체 실패

#### DELETE `/api/admin/posts/:id`

소프트 삭제. `deletedAt`을 현재 시각으로 설정한다.

#### PUT `/api/admin/posts/:id/restore`

`deletedAt`을 null로 되돌린다.

#### DELETE `/api/admin/posts/:id/hard`

하드 삭제. 연쇄 삭제 대상:
- 해당 게시글의 댓글 전체
- 해당 게시글의 조회수 통계
- 연결된 태그 관계 (post_tag_tb)
- 고아 태그 (다른 게시글에서 사용하지 않는 태그) 삭제

### PostDetail 스키마

```json
{
  "id": 1,
  "categoryId": 1,
  "title": "...",
  "slug": "...",
  "contentMd": "...",
  "summary": "...",
  "description": "...",
  "thumbnailUrl": "/uploads/example.jpg",
  "visibility": "public",
  "status": "published",
  "commentStatus": "open",
  "isPinned": false,
  "publishedAt": "ISO",
  "contentModifiedAt": "ISO",
  "createdAt": "ISO",
  "updatedAt": "ISO",
  "deletedAt": null,
  "category": {
    "id": 1, "name": "...", "slug": "...",
    "ancestors": [{ "name": "...", "slug": "..." }]
  },
  "tags": [{ "id": 1, "name": "...", "slug": "..." }],
  "totalPageviews": 245,
  "commentCount": 12
}
```

- `category.ancestors`: 루트부터 부모까지 순서. 직속 카테고리 자체는 포함하지 않음 (이미 `category.name`/`slug`로 제공).

### PostListItem 스키마

글 목록 API 응답 항목. `contentMd` 제외, 집계 필드 포함.

```json
{
  "id": 1,
  "categoryId": 1,
  "title": "...",
  "slug": "...",
  "summary": "...",
  "description": "...",
  "thumbnailUrl": "/uploads/example.jpg",
  "visibility": "public",
  "status": "published",
  "commentStatus": "open",
  "isPinned": false,
  "publishedAt": "ISO",
  "contentModifiedAt": "ISO",
  "createdAt": "ISO",
  "updatedAt": "ISO",
  "deletedAt": null,
  "category": { "id": 1, "name": "...", "slug": "..." },
  "tags": [{ "id": 1, "name": "...", "slug": "..." }],
  "totalPageviews": 245,
  "commentCount": 12
}
```

## 수용 기준

- [ ] Public GET `/api/posts`가 공개+발행 글만 반환하고 모든 query parameter를 지원한다
- [ ] Public GET `/api/posts`가 `status=published`, `visibility=public`, `deletedAt IS NULL`을 강제 적용한다
- [ ] GET `/api/posts/slugs`가 발행된 글의 slug + updatedAt만 반환한다
- [ ] GET `/api/posts/:slug`가 PostDetail과 prevPost/nextPost를 반환한다
- [ ] Admin GET `/api/admin/posts`가 모든 상태/가시성을 조회할 수 있고 includeDeleted를 지원한다
- [ ] Admin POST `/api/admin/posts`가 게시글을 생성하고 PostDetail을 반환한다
- [ ] Admin PATCH `/api/admin/posts/:id`가 게시글을 수정한다
- [ ] Admin PATCH `/api/admin/posts/bulk`가 벌크 작업을 단일 트랜잭션으로 수행한다
- [ ] Admin DELETE `/api/admin/posts/:id`가 소프트 삭제(deletedAt 설정)를 수행한다
- [ ] Admin PUT `/api/admin/posts/:id/restore`가 deletedAt을 null로 되돌린다
- [ ] Admin DELETE `/api/admin/posts/:id/hard`가 댓글, 조회수, 태그 관계, 고아 태그를 연쇄 삭제한다
- [ ] slug가 자동 생성되고 unique하다
- [ ] 모든 Admin 라우트가 `requireAdmin` 훅으로 보호된다

## 의존성

- Blocked by: S-03
- Blocks: S-05, S-10, S-12

## 참고

- PostListItem은 PostDetail에서 `contentMd`를 제외한 스키마이다.
- `category.ancestors`는 루트부터 부모까지의 순서이며, 직속 카테고리는 포함하지 않는다.
- 하드 삭제 시 고아 태그(다른 게시글에서 사용하지 않는 태그)도 함께 삭제한다.
- 벌크 작업은 단일 트랜잭션으로 전체 성공 or 전체 실패한다.
