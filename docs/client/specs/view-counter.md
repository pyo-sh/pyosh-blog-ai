# F-10: 조회수 기록

**상태:** DRAFT
**최종 수정:** 2026-03-20

---

## 1. 개요

글 상세 페이지(F-02) 방문 시 조회수를 기록하고, 글 상세 헤더와 글 목록(PostListItem)에 조회수를 표시한다. 서버 측 uniques 카운팅을 개선하여 일별 고유 방문자 수를 정확히 집계한다.

## 2. 배경 및 동기

현재 조회수 기록 기능이 구현되어 있으나 다음 개선이 필요하다:

- 조회수가 어디에도 표시되지 않음 (기록만 하고 표시 없음)
- `uniques` 카운팅이 부정확 (5분 캐시 만료 후 같은 IP가 재방문하면 uniques 중복 증가)
- `pageviews`와 `uniques` 값이 거의 동일하여 uniques가 무의미

## 3. 목표

- 글 상세 헤더에 조회수를 표시한다
- 글 목록 PostListItem에 조회수를 표시한다
- 서버 uniques 카운팅을 일별 고유 방문자 기준으로 개선한다
- Public에서는 pageviews만, Admin에서는 pageviews + uniques를 표시한다

## 4. 비목표

- 실시간 조회수 업데이트 (WebSocket)
- 조회수 기반 자동 정렬
- 조회수 그래프/차트 (F-20 대시보드 영역)

---

## 5. 상세 설계

### 5.1 조회수 표시 - 글 상세 헤더

글 상세 페이지 헤더의 메타 영역(날짜, 카테고리 옆)에 조회수를 표시한다.

```
┌─ 글 상세 헤더 ───────────────────────────────────┐
│                                                    │
│ 카테고리명                                          │
│ 글 제목이 여기에 표시됩니다                           │
│ 2026.03.15 · 조회 123                    ← 메타   │
│                                                    │
└────────────────────────────────────────────────────┘
```

- `조회 123`: `text-body-sm`, `text-text-3`
- 숫자 포맷: 한국어 로케일 (`1,234`)
- 서버에서 해당 글의 `pageviews` 합산값을 조회하여 전달

### 5.2 조회수 표시 - PostListItem (글 목록)

PostListItem 메타 영역에 조회수를 추가한다.

```
┌─ PostListItem ────────────────────────────────────────┐
│ [썸네일]                                           │
│ 카테고리 · 2026.03.15 · 조회 123         ← 메타   │
│ 글 제목                                            │
│ 글 요약 텍스트...                                   │
│ #태그1 #태그2                                       │
└────────────────────────────────────────────────────┘
```

- 기존 메타 구분자(`·`)와 동일한 스타일
- `text-body-xs`, `text-text-4`

### 5.3 조회수 데이터 제공

#### 글 상세

`GET /api/posts/:slug` 응답에 `totalPageviews` 필드를 추가한다.

```typescript
interface PostDetail {
  // ...기존 필드
  totalPageviews: number;  // 전체 기간 pageviews 합산
}
```

서버에서 `stats_daily_tb`의 해당 post_id pageviews를 `SUM()`으로 집계하여 포함한다.

#### 글 목록

`GET /api/posts` 응답의 각 글 항목에 `totalPageviews` 필드를 추가한다.

```typescript
interface PostListItem {
  // ...기존 필드
  totalPageviews: number;
}
```

서버에서 글 목록 조회 시 `stats_daily_tb`를 LEFT JOIN하여 각 글의 pageviews 합산을 포함한다.

### 5.4 조회수 기록 - 클라이언트

#### 글별 조회수 (기존 유지)

```
ViewCounter (Client Component, 렌더링 null)
  └─ useViewCount(postId)
     ├─ sessionStorage 중복 체크 (viewed_posts)
     ├─ pending 체크 (pending_viewed_posts, 5분 TTL)
     ├─ inFlight Set 체크 (동시 요청 방지)
     └─ POST /api/stats/view { postId } (keepalive: true)
```

#### 사이트 전체 조회수 (신규)

루트 레이아웃(`app/layout.tsx`)에 `SiteViewCounter`를 배치하여 모든 페이지 방문을 기록한다.

```
SiteViewCounter (Client Component, 렌더링 null)
  └─ useSiteViewCount()
     ├─ sessionStorage 중복 체크 (site_viewed)
     ├─ pending 체크 (pending_site_view, 5분 TTL)
     └─ POST /api/stats/view {} (postId 없음, keepalive: true)
```

- `postId`를 보내지 않으면 서버에서 사이트 전체 조회수(`postId: NULL`)로 기록
- 글 상세 방문 시: 글별 + 사이트 전체 **둘 다** 기록됨 (별도 요청)
- sessionStorage 키를 분리하여 글별/사이트 전체 중복 체크가 독립적으로 동작

### 5.5 서버 uniques 카운팅 개선

#### 캐시 분리

```
변경 전: 단일 캐시 {postId}:{ip} → TTL 5분
변경 후: 두 개의 캐시
  - pageview 캐시: {key}:{ip} → TTL 5분 (연타 방지)
  - unique 캐시: {key}:{ip}:{kstDate} → KST 자정까지 (일별 고유 방문자)
```

- `key`: 글별은 `postId`, 사이트 전체는 `"site"`
- `kstDate`: KST(UTC+9) 기준 날짜 문자열 (`"2026-03-25"`)

#### KST 기준 날짜 산출

unique 초기화는 **한국 시간 자정(00:00 KST)**을 기준으로 한다.

```typescript
function getKSTDate(): string {
  const now = new Date();
  const kst = new Date(now.getTime() + 9 * 60 * 60 * 1000);
  return kst.toISOString().slice(0, 10); // "2026-03-25"
}
```

- DB의 `date` 컬럼도 `CURDATE()` 대신 `getKSTDate()` 값을 사용
- unique 캐시 TTL: KST 자정까지 남은 시간으로 동적 설정, 또는 최대 24시간 고정 (KST date가 키에 포함되므로 날짜 변경 시 자동 분리)

#### incrementView 로직 (글별 + 사이트 전체 공통)

```
입력: postId (nullable), ip
key = postId ?? "site"

1. pageview 캐시 확인 ({key}:{ip})
   └─ 히트 → 전체 스킵 (deduplicated=true)

2. pageview 캐시 미스 → pageview 캐시 등록 (TTL 5분)

3. kstDate = getKSTDate()
   unique 캐시 확인 ({key}:{ip}:{kstDate})
   ├─ 히트 → pageviews만 +1
   └─ 미스 → pageviews +1, uniques +1, unique 캐시 등록 (TTL 24시간)
```

#### DB 업데이트 분기

```sql
-- unique 캐시 미스 (새 고유 방문자)
INSERT INTO stats_daily_tb (post_id, date, pageviews, uniques)
VALUES (:postIdOrNull, :kstDate, 1, 1)
ON DUPLICATE KEY UPDATE
  pageviews = pageviews + 1,
  uniques = uniques + 1;

-- unique 캐시 히트 (재방문)
INSERT INTO stats_daily_tb (post_id, date, pageviews, uniques)
VALUES (:postIdOrNull, :kstDate, 1, 0)
ON DUPLICATE KEY UPDATE
  pageviews = pageviews + 1;
```

- `postIdOrNull`: 글별이면 postId, 사이트 전체면 NULL
- `kstDate`: KST 기준 날짜 (`getKSTDate()`)

#### 결과 예시

```
같은 IP, 같은 글, KST 기준 같은 날:
  10:00 KST → pageviews +1, uniques +1  (첫 방문)
  10:02 KST → 스킵 (5분 캐시)
  10:07 KST → pageviews +1만 (unique 캐시 유지)
  15:00 KST → pageviews +1만 (unique 캐시 유지)

KST 자정 이후 (다음 날):
  00:05 KST → pageviews +1, uniques +1  (새 KST 날짜, unique 캐시 키 변경)

결과: pageviews=4, uniques=2 (이틀간 같은 사람)

사이트 전체 (postId = NULL):
  홈 방문 → site pageviews +1
  글 상세 방문 → site pageviews +1 + post pageviews +1 (별도 요청)
  태그 페이지 방문 → site pageviews +1
```

### 5.6 Admin 조회수 표시

Admin에서는 pageviews와 uniques를 모두 표시한다.

- **F-20 대시보드**: 기존 통계 요약에 uniques 포함
- **F-21 글 관리**: 글 목록에 pageviews / uniques 두 값 표시
- **인기글 API**: `GET /api/stats/popular` 응답에 이미 두 값 포함 (변경 없음)

Public에서는 `pageviews`만 "조회 N"으로 표시하고 `uniques`는 노출하지 않는다.

### 5.7 컴포넌트 구조 (FSD)

| 계층 | 파일 | 역할 |
|---|---|---|
| `features` | `post-detail/ui/view-counter.tsx` | 글별 조회수 기록 (기존, 렌더링 null) |
| `features` | `site-view-counter/ui/site-view-counter.tsx` | 사이트 전체 조회수 기록 (신규, 렌더링 null) |
| `shared` | `hooks/use-view-count.ts` | 글별 조회수 기록 훅 (기존) |
| `shared` | `hooks/use-site-view-count.ts` | 사이트 전체 조회수 기록 훅 (신규) |
| `entities` | `stat/api.ts` | `fetchPopularPosts`, `fetchTotalViews` |
| `entities` | `stat/model.ts` | `PopularPost` 타입 (기존) |
| `features` | `post-list/ui/post-list-item.tsx` | PostListItem에 조회수 표시 추가 |

### 5.8 데이터 흐름

```
루트 레이아웃 (모든 페이지)
  └─ SiteViewCounter → useSiteViewCount() → POST /api/stats/view {}

글 상세 페이지 (Server Component)
  ├─ fetchPost(slug) → totalPageviews 포함
  ├─ 헤더 메타에 "조회 {totalPageviews}" 표시
  └─ ViewCounter → useViewCount(postId) → POST /api/stats/view { postId }

글 목록 페이지 (Server Component)
  ├─ fetchPosts() → 각 항목에 totalPageviews 포함
  └─ PostListItem 메타에 "조회 {totalPageviews}" 표시
```

## 6. API 연동

| 메서드 | 경로 | 용도 | 변경 사항 |
|---|---|---|---|
| POST | `/api/stats/view` | 조회수 기록 | postId 선택적 (없으면 사이트 전체), KST 기준 unique |
| GET | `/api/stats/total-views` | 사이트 전체 누적 조회수 | **신규** |
| GET | `/api/posts/:slug` | 글 상세 | `totalPageviews` 필드 추가 |
| GET | `/api/posts` | 글 목록 | `totalPageviews` 필드 추가 |
| GET | `/api/stats/popular` | 인기글 | 없음 (기존) |

### 서버 변경 필요사항

| 항목 | 설명 |
|---|---|
| `StatsService.incrementView()` | postId nullable 처리, KST 기준 날짜, unique 캐시 분리 |
| `StatsService.getTotalViews()` | `SUM(pageviews) WHERE postId IS NULL` 반환 (신규) |
| `StatsRoute` | `POST /api/stats/view` body에서 postId 선택적, `GET /api/stats/total-views` 추가 |
| `PostService.getPostBySlug()` | `stats_daily_tb` JOIN으로 `totalPageviews` 포함 |
| `PostService.getPostList()` | `stats_daily_tb` LEFT JOIN으로 `totalPageviews` 포함 |

## 7. 수용 기준

- [ ] 글 상세 헤더에 "조회 N" 형태로 조회수가 표시된다
- [ ] PostListItem 메타에 "조회 N" 형태로 조회수가 표시된다
- [ ] 숫자가 한국어 로케일로 포맷된다 (1,234)
- [ ] 같은 IP의 KST 같은 날 재방문 시 uniques가 증가하지 않는다
- [ ] KST 자정 이후 방문 시 uniques가 증가한다
- [ ] pageviews는 5분 캐시 만료 후 재방문 시 정상 증가한다
- [ ] 모든 페이지 방문 시 사이트 전체 조회수(`postId: NULL`)가 기록된다
- [ ] `GET /api/stats/total-views`가 사이트 전체 누적 pageviews를 반환한다
- [ ] Public에서 uniques는 표시되지 않는다
- [ ] Admin에서 pageviews와 uniques 모두 표시된다
- [ ] 글 상세/목록 API 응답에 totalPageviews가 포함된다
- [ ] 다크모드 자동 적용
- [ ] Storybook story 작성 (F-38 참조)

## 8. 에지 케이스

| 케이스 | 처리 |
|---|---|
| 조회수 0인 글 | "조회 0" 표시 |
| stats 테이블에 데이터 없는 글 | LEFT JOIN으로 null → 0 처리 |
| 서버 캐시 메모리 증가 | 주기적 pruning (기존 구현 유지) |
| 봇/크롤러 방문 | Rate limit 30req/min으로 제한 (기존) |
| keepalive 요청 실패 | 클라이언트 pending 상태 유지, 재시도 안 함 (기존) |

## 9. 의존성

- F-02 글 상세 (표시 위치)
- F-01 홈 - 글 목록 (PostListItem 표시)

## 10. 미해결 사항

없음. 모든 사항 확정됨.
