# Progress: 2026-03-06

## Completed
- [x] #46 Admin 레이아웃 (사이드바) 구현
  - AdminSidebar 위젯: 대시보드, 글 관리, 카테고리, 댓글, 방명록, 에셋 메뉴
  - usePathname 기반 활성 메뉴 하이라이트
  - dashboard/layout.tsx: 좌측 사이드바(240px) + 메인 컨텐츠
  - dashboard/page.tsx: 대시보드 플레이스홀더 페이지
- [x] #50 Post create/update/fetch API functions (model.ts, api.ts, index.ts) - PR #122
  - `CreatePostBody`, `UpdatePostBody` type definitions
  - `fetchAdminPost`, `createPost`, `updatePost` functions
  - Used `clientMutate` for CSRF-protected mutations, `serverFetch` for SSR reads
  - 3 review rounds: type mismatches fixed (id/categoryId string->number, tags string[]->PostTag[], status added `archived`), `PostDetailResponse` wrapper unwrap, `cookieHeader` made required
- [x] #42 Stat entity (대시보드) - PR pending
  - `DashboardStats` 타입 (todayPageviews, weekPageviews, monthPageviews, totalPosts, totalComments)
  - `fetchDashboardStats()` - clientFetch('/api/admin/stats/dashboard')
  - tsconfig.alias.json에 `@/*` 경로 추가로 `@/shared/api` import resolve 근본 수정

## Issues & resolutions
- **Issue**: `@/shared/api` import alias not defined in tsconfig - pre-existing bug from #38
- **Resolution**: Fixed to `@shared/api` (matching tsconfig.alias.json paths) in both auth/api.ts and post/api.ts
- **Issue**: Return types declared as `Promise<Post>` but backend returns `{ post: ... }` wrapper
- **Resolution**: Added `PostDetailResponse` type, unwrap `response.post` in all API functions
- **Issue**: `cookieHeader` was optional on `fetchAdminPost` (server-only function)
- **Resolution**: Made required to match `fetchMeServer` pattern in auth/api.ts
