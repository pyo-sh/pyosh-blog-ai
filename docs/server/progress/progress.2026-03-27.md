# Server Progress - 2026-03-27

## Issue #42 Stats API - PR #59 머지

### 구현 내용

4개 엔드포인트 구현:

- `POST /api/stats/view` - 조회수 기록 (postId 선택적, CSRF, 30 req/min rate limit)
- `GET /api/stats/popular` - 기간별 인기 게시글 (limit/days 파라미터)
- `GET /api/stats/total-views` - 사이트 전체 누적 조회수
- `GET /api/admin/stats/dashboard` - 대시보드 통계 (Admin)

### 주요 변경 사항

**`src/routes/stats/stats.schema.ts`**
- `StatsViewBodySchema.postId` 선택적으로 변경
- `TotalViewsResponseSchema` 추가
- `DashboardStatsResponseSchema`에 `postsByStatus` 필드 추가

**`src/routes/stats/stats.route.ts`**
- `GET /api/stats/total-views` 엔드포인트 추가
- POST 핸들러에서 선택적 `postId` 전달

**`src/services/stats.service.ts`**
- `incrementPageView(postId: number | undefined, ip)` - postId 선택적 처리
- KST 날짜 사용: `DATE(CONVERT_TZ(NOW(), '+00:00', '+09:00'))`
- `getTotalViews()` 메서드 추가
- `getDashboardStats()`에 `postsByStatus` 집계 추가

**`src/db/schema/stats.ts`**
- `postId` 컬럼에 `.notNull()` 추가 (0 = 사이트 전체 센티넬)

**`drizzle/0006_stats_post_id_not_null.sql`**
- NULL 행을 0으로 업데이트 후 NOT NULL 제약 추가

**`test/routes/stats.test.ts`** (신규)
- 4개 엔드포인트에 대한 통합 테스트 13건

### 핵심 기술 결정

**postId=0 센티넬 전략**: MySQL unique index에서 `NULL != NULL`로 처리되어 `ON DUPLICATE KEY UPDATE`가 사이트 전체 조회수 행에 동작하지 않는 버그 수정. `NULL` 대신 `postId=0`을 사이트 전체 센티넬 값으로 사용하고, DB 컬럼을 NOT NULL로 변경.
