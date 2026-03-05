# Progress: 2026-03-06

## Completed
- [x] #46 Admin 레이아웃 (사이드바) 구현
  - AdminSidebar 위젯: 대시보드, 글 관리, 카테고리, 댓글, 방명록, 에셋 메뉴
  - usePathname 기반 활성 메뉴 하이라이트
  - dashboard/layout.tsx: 좌측 사이드바(240px) + 메인 컨텐츠
  - dashboard/page.tsx: 대시보드 플레이스홀더 페이지
- [x] #50 Post create/update/fetch API functions (model.ts, api.ts, index.ts)
  - `CreatePostBody`, `UpdatePostBody` type definitions
  - `fetchAdminPost`, `createPost`, `updatePost` functions
  - Used `clientMutate` for CSRF-protected mutations, `serverFetch` for SSR reads

## Issues & resolutions
- **Issue**: `@/shared/api` import alias not defined in tsconfig - pre-existing bug from #38
- **Resolution**: Fixed to `@shared/api` (matching tsconfig.alias.json paths) in both auth/api.ts and post/api.ts

## Notes
- Also fixed ESLint import/order: relative type imports before aliased imports
