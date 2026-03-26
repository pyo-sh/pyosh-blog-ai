# Categories API

> 카테고리 관리 엔드포인트 5개 구현 (트리 조회, CRUD, 배치 순서 변경)

## SPEC 참조

- `docs/server/api-spec.md` > Categories 섹션

## 상세

### 엔드포인트

| Method | Path | Auth | 설명 |
|---|---|---|---|
| GET | `/api/categories` | - | 카테고리 트리 (Cache: 300s) |
| POST | `/api/categories` | Admin | 카테고리 생성 |
| PATCH | `/api/categories/:id` | Admin | 카테고리 수정 |
| PATCH | `/api/categories/tree` | Admin | 카테고리 트리 배치 변경 (parentId, sortOrder) |
| DELETE | `/api/categories/:id` | Admin | 카테고리 삭제 |

#### GET `/api/categories`

**Query:** `?include_hidden=true` (관리자 세션일 때만 적용)

> 카테고리 조회는 트리 엔드포인트(`GET /api/categories`) 하나로 통합한다.

**Response 200:**
```json
{
  "categories": [{
    "id": 1, "parentId": null, "name": "...", "slug": "...",
    "sortOrder": 0, "isVisible": true,
    "publishedPostCount": 3, "totalPostCount": 5,
    "createdAt": "ISO", "updatedAt": "ISO",
    "children": [CategoryTree]
  }]
}
```

- Cache: 300s (5분)
- `include_hidden=true`는 관리자 세션에서만 적용된다
- `publishedPostCount`: 해당 카테고리의 공개+발행 게시글 수
- `totalPostCount`: 해당 카테고리의 전체 게시글 수 (관리자용)

#### POST `/api/categories`

**Request Body:**
```json
{ "name": "string (1-50)", "parentId": 1, "isVisible": true }
```

**Response 201:** `{ "category": Category }`

- slug는 name에서 자동 생성된다

#### PATCH `/api/categories/:id`

**Request Body:**
```json
{ "name": "string (1-50)", "parentId": 1, "sortOrder": 0, "isVisible": true }
```

모든 필드 optional.

#### PATCH `/api/categories/tree`

**Request Body:**
```json
{ "changes": [{ "id": 1, "parentId": null, "sortOrder": 0 }, { "id": 2, "parentId": 1, "sortOrder": 1 }] }
```

- 단일 트랜잭션: 전체 성공 or 전체 실패
- 프론트엔드 드래그앤드롭 트리 재정렬에 사용

**Response 200:** `{ "success": true }`

#### DELETE `/api/categories/:id`

**Query:** `?action=move&moveTo=3` 또는 `?action=trash`

- `move`: 해당 카테고리의 글을 `moveTo` 카테고리로 이동 후 삭제
- `trash`: 해당 카테고리의 글을 휴지통으로 이동 후 삭제

### CategoryTree 스키마

재귀적 트리 구조:

```json
{
  "id": 1,
  "parentId": null,
  "name": "...",
  "slug": "...",
  "sortOrder": 0,
  "isVisible": true,
  "publishedPostCount": 3,
  "totalPostCount": 5,
  "createdAt": "ISO",
  "updatedAt": "ISO",
  "children": [CategoryTree]
}
```

## 수용 기준

- [ ] GET `/api/categories`가 재귀적 트리 구조로 카테고리를 반환한다
- [ ] 응답에 300초 캐시가 적용된다
- [ ] `include_hidden=true`가 관리자 세션에서만 동작한다
- [ ] publishedPostCount와 totalPostCount가 정확히 계산된다
- [ ] POST `/api/categories`가 카테고리를 생성하고 slug를 자동 생성한다
- [ ] PATCH `/api/categories/:id`가 부분 업데이트를 지원한다
- [ ] PATCH `/api/categories/tree`가 단일 트랜잭션으로 배치 변경한다
- [ ] DELETE에서 `action=move`가 글을 지정 카테고리로 이동 후 삭제한다
- [ ] DELETE에서 `action=trash`가 글을 휴지통으로 이동 후 삭제한다
- [ ] 하위 카테고리가 있는 카테고리 삭제 시 적절히 처리된다
- [ ] 모든 관리자 엔드포인트가 `requireAdmin` 훅으로 보호된다

## 의존성

- Blocked by: S-03
- Blocks: S-12

## 참고

- 카테고리는 self-FK 기반 트리 구조이다. `parentId`가 null이면 루트 카테고리이다.
- 트리 배치 변경은 프론트엔드에서 드래그앤드롭으로 카테고리 순서/계층을 변경할 때 사용한다.
- 카테고리 삭제 시 해당 카테고리에 속한 게시글 처리 방식(move/trash)을 반드시 지정해야 한다.
