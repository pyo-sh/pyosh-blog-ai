# Guestbook + settings API

> 방명록 공개/관리자 엔드포인트 6개 + 방명록 설정 엔드포인트 2개 구현

## SPEC 참조

- `docs/server/api-spec.md` > Guestbook (Public + Admin), Settings, CSRF 보호, Rate limiting

## 상세

### Public 엔드포인트 (`/api`)

| Method | Path | Auth | 설명 |
|---|---|---|---|
| GET | `/api/guestbook` | optionalAuth | 방명록 목록 (페이지네이션) |
| POST | `/api/guestbook` | optionalAuth, CSRF | 방명록 작성 (guestbook_enabled 확인, 10 req/min) |
| DELETE | `/api/guestbook/:id` | optionalAuth, CSRF | 방명록 소프트 삭제 (게스트: 비밀번호 필요, body 보존) |

### Admin 엔드포인트 (`/api/admin`)

| Method | Path | Auth | 설명 |
|---|---|---|---|
| GET | `/api/admin/guestbook` | Admin | 방명록 목록 (필터 + 검색 + 페이지네이션) |
| DELETE | `/api/admin/guestbook/:id` | Admin | 방명록 삭제 (`?action=hide` \| `?action=soft_delete` \| `?action=hard_delete`) |
| DELETE | `/api/admin/guestbook/bulk` | Admin | 방명록 벌크 삭제 |

### Settings 엔드포인트 (`/api/settings`)

| Method | Path | Auth | 설명 |
|---|---|---|---|
| GET | `/api/settings/guestbook` | - | 방명록 활성 상태 조회 |
| PATCH | `/api/admin/settings/guestbook` | Admin | 방명록 활성 상태 변경 |

#### GET `/api/guestbook`

**Query:** `?page=1&limit=20` (max 100)

**Response 200:**
```json
{
  "data": [GuestbookEntryDetail],
  "meta": { "page": 1, "limit": 20, "totalCount": 50, "totalPages": 3 }
}
```

#### POST `/api/guestbook`

서버는 먼저 guestbook_enabled 설정을 확인한다. 비활성 시 403을 반환한다.

**OAuth 사용자:**
```json
{ "body": "string (1-2000)", "parentId": 1, "isSecret": false }
```

**게스트:**
```json
{ "body": "...", "parentId": 1, "isSecret": false,
  "guestName": "string (1-50)", "guestEmail": "string (email)", "guestPassword": "string (4-100)" }
```

- CSRF 토큰 필요
- Rate limit: 10 req/min

#### DELETE `/api/guestbook/:id`

**Body (게스트만):**
```json
{ "guestPassword": "string (min 4)" }
```

- CSRF 토큰 필요
- 소프트 삭제 (body 보존, status/deletedAt만 변경)

#### GET `/api/admin/guestbook`

**Query Parameters:**

| Param | Type | Default | 설명 |
|---|---|---|---|
| page | number | 1 | 페이지 번호 |
| limit | number (max 100) | 20 | 페이지당 개수 |
| status | string | - | 상태 필터 (`active` \| `deleted` \| `hidden`) |
| authorType | string | - | 작성자 유형 (`oauth` \| `guest`) |
| q | string | - | 작성자 이름 + 본문 검색 |
| startDate | string | - | 시작일 (YYYY-MM-DD) |
| endDate | string | - | 종료일 (YYYY-MM-DD) |

**Response 200:**
```json
{
  "data": [GuestbookEntryDetail],
  "meta": { "page": 1, "limit": 20, "totalCount": 50, "totalPages": 3 }
}
```

#### DELETE `/api/admin/guestbook/:id`

**Query:** `?action=hide` 또는 `?action=soft_delete` 또는 `?action=hard_delete`

- `hide`: status를 hidden으로 변경 (공개 목록에서 숨김)
- `soft_delete`: body 보존, status/deletedAt만 변경
- `hard_delete`: DB에서 완전 삭제

#### DELETE `/api/admin/guestbook/bulk`

**Request Body:**
```json
{ "ids": [1, 2, 3], "action": "hide | restore | soft_delete | hard_delete" }
```

#### GET `/api/settings/guestbook`

**Response 200:**
```json
{ "enabled": true }
```

#### PATCH `/api/admin/settings/guestbook`

**Request Body:**
```json
{ "enabled": true }
```

## 수용 기준

- [ ] GET `/api/guestbook`가 페이지네이션된 방명록 목록을 반환한다
- [ ] POST `/api/guestbook`이 guestbook_enabled 설정을 확인하고, 비활성 시 403을 반환한다
- [ ] POST `/api/guestbook`이 게스트/OAuth 방명록을 생성한다
- [ ] 방명록 작성 시 CSRF 토큰이 검증된다
- [ ] 방명록 작성에 10 req/min rate limit이 적용된다
- [ ] 게스트 방명록에 guestName, guestEmail, guestPassword가 필요하다
- [ ] 게스트 비밀번호가 해시되어 저장된다
- [ ] DELETE `/api/guestbook/:id`가 게스트 비밀번호를 확인 후 소프트 삭제한다
- [ ] 방명록 삭제 시 CSRF 토큰이 검증된다
- [ ] Admin GET `/api/admin/guestbook`가 필터/검색/페이지네이션을 지원한다
- [ ] Admin DELETE가 hide/soft_delete/hard_delete action을 지원한다
- [ ] Admin 벌크 삭제가 hide/restore/soft_delete/hard_delete를 지원한다
- [ ] GET `/api/settings/guestbook`가 활성 상태를 반환한다
- [ ] PATCH `/api/admin/settings/guestbook`가 활성 상태를 변경한다

## 의존성

- Blocked by: S-03
- Blocks: 없음

## 참고

- 방명록과 댓글 구조가 유사하지만 방명록은 특정 게시글에 속하지 않는 독립 엔티티이다.
- `hide` action은 공개 목록에서만 숨기고, `soft_delete`는 status + deletedAt을 변경한다.
- 비밀글(`isSecret: true`) 마스킹 규칙은 댓글과 동일하다.
- 게스트 비밀번호는 반드시 해시하여 저장한다.
