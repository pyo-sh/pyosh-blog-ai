# Stats API

> 조회수 기록/조회 및 대시보드 통계 엔드포인트 4개 구현

## SPEC 참조

- `docs/server/api-spec.md` > Stats (Public + Admin), CSRF 보호, Rate limiting

## 상세

### Public 엔드포인트 (`/api/stats`)

| Method | Path | Auth | 설명 |
|---|---|---|---|
| POST | `/api/stats/view` | CSRF | 조회수 기록 (postId 선택적, 같은 IP 5분 내 중복 제거, KST 기준 unique, 30 req/min) |
| GET | `/api/stats/popular` | - | 인기 게시글 |
| GET | `/api/stats/total-views` | - | 사이트 전체 누적 조회수 |

### Admin 엔드포인트 (`/api/admin/stats`)

| Method | Path | Auth | 설명 |
|---|---|---|---|
| GET | `/api/admin/stats/dashboard` | Admin | 대시보드 통계 |

#### POST `/api/stats/view`

**Request Body:**
```json
{ "postId": 1 }
```

- `postId` 선택적: 있으면 글별 조회수, 없으면 사이트 전체 조회수 (`postId: NULL`)
- 같은 IP 5분 내 중복 제거
- unique 기준: KST(UTC+9) 자정 초기화
- CSRF 토큰 필요
- Rate limit: 30 req/min

**Response 200:**
```json
{ "success": true, "deduplicated": false }
```

- `deduplicated: true`는 중복 요청으로 카운트에 반영되지 않았음을 의미한다

#### GET `/api/stats/popular`

**Query:** `?limit=10&days=7` (max limit=100, max days=365)

**Response 200:**
```json
{ "data": [{ "postId": 1, "slug": "...", "title": "...", "pageviews": 100, "uniques": 80 }] }
```

#### GET `/api/stats/total-views`

**Response 200:**
```json
{ "totalPageviews": 12345 }
```

- `stats_daily_tb`에서 `postId IS NULL`인 행의 `SUM(pageviews)` 반환

#### GET `/api/admin/stats/dashboard`

**Response 200:**
```json
{
  "todayPageviews": 50,
  "weekPageviews": 300,
  "monthPageviews": 1200,
  "totalPosts": 25,
  "totalComments": 150,
  "postsByStatus": { "draft": 5, "published": 18, "archived": 2 }
}
```

### 조회수 기록 로직

1. 요청의 IP와 postId(또는 null)를 기반으로 중복 확인
2. 같은 IP에서 5분 내 동일 대상(postId 또는 site)에 대한 요청은 무시
3. `stats_daily_tb`에서 해당 날짜(KST 기준)의 레코드를 찾아 pageviews +1
4. KST 자정을 기준으로 unique 카운트 초기화

## 수용 기준

- [ ] POST `/api/stats/view`가 조회수를 기록한다
- [ ] postId가 있으면 글별 조회수, 없으면 사이트 전체 조회수를 기록한다
- [ ] 같은 IP에서 5분 내 동일 대상 조회수 요청이 중복 제거된다
- [ ] unique 카운트가 KST(UTC+9) 자정 기준으로 초기화된다
- [ ] CSRF 토큰이 검증된다
- [ ] 30 req/min rate limit이 적용된다
- [ ] `deduplicated` 필드로 중복 여부를 응답한다
- [ ] GET `/api/stats/popular`가 기간별 인기 게시글을 반환한다
- [ ] limit (max 100)과 days (max 365) 파라미터가 동작한다
- [ ] GET `/api/stats/total-views`가 사이트 전체 누적 조회수를 반환한다
- [ ] GET `/api/admin/stats/dashboard`가 대시보드 통계를 반환한다
- [ ] 대시보드에 todayPageviews, weekPageviews, monthPageviews, totalPosts, totalComments, postsByStatus가 포함된다

## 의존성

- Blocked by: S-03, S-04
- Blocks: 없음

## 참고

- `stats_daily_tb`에서 `postId IS NULL`인 행은 사이트 전체 조회수를 나타낸다.
- 중복 제거는 메모리 기반(Map 등)으로 구현 가능하다. Redis는 사용하지 않는다.
- KST(UTC+9) 기준 날짜 계산에 주의한다.
- popular 엔드포인트는 공개+발행 게시글만 대상으로 한다.
