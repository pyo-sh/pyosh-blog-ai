# Server Progress - 2026-03-27

## Issue #41 Posts admin CRUD — tests + pagination meta fix (PR #62)

**관련 이슈:** #41 [S-04b] Posts admin CRUD
**PR:** pyo-sh/pyosh-blog-be#62 (merged)

### 작업 내용

4개 admin CRUD 엔드포인트의 통합 테스트 추가 및 pagination meta 버그 수정.

**구현 범위:** `GET /api/admin/posts`, `POST /api/admin/posts`, `GET /api/admin/posts/:id`, `PATCH /api/admin/posts/:id`

#### 추가된 테스트 (16건)

| 엔드포인트 | 테스트 케이스 |
|---|---|
| `POST /api/admin/posts` | slug 자동 생성 확인, 중복 slug suffix 처리, status=published → publishedAt 자동 설정 |
| `PATCH /api/admin/posts/:id` | contentMd 수정 → contentModifiedAt 갱신, tags=[] → 전체 태그 제거, 존재하지 않는 ID → 404, 비인증 → 403 |
| `GET /api/admin/posts/:id` | contentMd 포함 PostDetail 반환, 중첩 카테고리 ancestors 반환, 존재하지 않는 ID → 404, 비인증 → 403 |
| `GET /api/admin/posts` | status 필터, visibility 필터, includeDeleted=true, 페이지네이션 meta 검증, 비인증 → 403 |

#### 버그 수정: `buildPaginatedResponse` 파라미터 순서 오류

`post.service.ts`의 `getPostList`에서 `buildPaginatedResponse` 호출 순서가 잘못되어 있었음.

```typescript
// 수정 전 (잘못됨): (data, page, limit, total)
return buildPaginatedResponse(postsWithDetails, page, limit, total);

// 수정 후 (올바름): (data, total, page, limit)
return buildPaginatedResponse(postsWithDetails, total, page, limit);
```

함수 시그니처 `(data, total, page, limit)`와 순서가 달라 `meta.total`, `meta.page`, `meta.limit` 모두 잘못된 값이 반환되고 있었음. 빈 배열 반환 early-return 6곳도 동일하게 수정. 기존 테스트가 `meta` 필드를 검증하지 않아 발견되지 않았던 잠재적 버그.

### 변경 파일

- `src/routes/posts/post.service.ts` - buildPaginatedResponse 파라미터 순서 수정 (7곳)
- `test/routes/posts.test.ts` - 통합 테스트 16건 추가 (30 → 46 tests)

---

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

---

## Issue #40 Comments public API - PR #61 머지

**관련 이슈:** #40 [S-05a] Comments public API
**PR:** pyo-sh/pyosh-blog-be#61 (merged)

### 작업 내용

Public 댓글 API 페이지네이션 + 전체 Admin CRUD 구현. 기존 구현에서 누락된 기능들을 완성.

**구현 범위:**
- `GET /api/posts/:postId/comments` - 루트 댓글 기준 페이지네이션, replies 인라인 포함
- `POST /api/posts/:postId/comments` - 게스트/OAuth, 대댓글(depth 1 제한), 비밀글
- `DELETE /api/comments/:id` - 게스트 비밀번호 검증, OAuth 본인 확인, CSRF
- `GET /api/admin/comments` - status/sort/order 필터 추가, post.title 포함
- `GET /api/admin/comments/:id/thread` - 루트 댓글 + 모든 답글 반환 (답글 ID 전달 시 루트로 정규화)
- `PUT /api/admin/comments/:id/restore` - deleted → active 복원 (status guard)
- `DELETE /api/admin/comments/:id` - `?action=soft_delete|hard_delete` 파라미터
- `DELETE /api/admin/comments/bulk` - restore/soft_delete/hard_delete 벌크 작업

### 주요 변경 사항

**`src/routes/comments/comment.schema.ts`**
- `CommentsQuerySchema` - page/limit (루트 댓글 기준 페이지네이션)
- `CommentsPaginationMetaSchema` - totalCount, totalRootComments, totalPages
- `AdminCommentListQuerySchema`에 status, sort, order 필드 추가
- `AdminCommentItemSchema`에 `post: { id, title }` 필드 추가
- `AdminCommentThreadResponseSchema`, `AdminCommentDeleteQuerySchema`, `AdminCommentRestoreResponseSchema`, `AdminCommentBulkBodySchema` 신규 추가

**`src/routes/comments/comment.service.ts`**
- `getCommentsByPostId` - 루트 댓글만 페이지네이션, replies 별도 조회 후 계층 병합
- `getAdminComments` - status/sort/order 필터, 게시글 N+1 제거 (postId batch fetch → Map)
- `getAdminCommentThread` - 루트 ID 정규화 로직 포함
- `restoreComment` - status='deleted' guard
- `deleteComment` - hardDelete 파라미터 추가, 트랜잭션으로 cascade 삭제
- `bulkOperateComments` - restore/soft_delete/hard_delete; restore는 status='deleted' 조건, soft_delete는 status='active' 조건으로 hidden 댓글 보호; hard_delete는 트랜잭션 처리

**`test/routes/comments.test.ts`**
- 24건 → 28건: 페이지네이션 메타, status 필터, thread (루트/답글 ID), restore 왕복, soft/hard delete, bulk cascade 테스트 추가

### 핵심 기술 결정

**루트 댓글 기준 페이지네이션**: 페이지네이션은 depth=0(루트) 댓글에만 적용. 현재 페이지의 루트 IDs를 수집 후 replies를 별도 IN-clause 쿼리로 가져와 계층 병합. totalCount(전체)와 totalRootComments(페이지 기준)를 분리 제공.

**status guard 일관성**: restore(deleted→active), soft_delete(active→deleted) 모두 status 조건으로 hidden 댓글 보호. hidden 상태는 별도 관리 플로우로 취급.

**Hard delete 원자성**: 자식 댓글 삭제 + 부모 삭제를 트랜잭션으로 묶어 중간 실패 시 고아 레코드 방지.
