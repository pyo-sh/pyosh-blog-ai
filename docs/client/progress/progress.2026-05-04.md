# Client Progress — 2026-05-04

## #374 Admin 로그아웃 시 클라이언트 민감 캐시 정리

- Issue: pyo-sh/pyosh-blog-fe#374
- PR: pyo-sh/pyosh-blog-fe#384
- 상태: 머지 완료

## 작업 내용

- `AdminLogoutButton`에서 `/auth/admin/logout` 성공 후 React Query `queryClient.clear()`를 호출하도록 연결했다.
- 로그아웃 성공 후 module-level CSRF `tokenPromise`가 남지 않도록 `clearCsrfToken()`을 호출했다.
- 서버 로그아웃 실패 시에는 기존처럼 toast만 표시하고 클라이언트 cache/token 정리는 수행하지 않도록 성공 경로에만 정리를 배치했다.
- 정리 이후 기존 흐름대로 `/manage/login` 이동과 `router.refresh()`를 수행한다.

## 검증

- `pnpm compile:types`
- `pnpm lint` (기존 unrelated warning 2건 유지)
- `pnpm build`
- 자동 리뷰: Critical 0, Warning 0, Suggestion 0
