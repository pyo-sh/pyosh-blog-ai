# Client Progress — 2026-05-04

## #375 Admin 인증 경계에서 클라이언트 민감 상태 정리

- Issue: pyo-sh/pyosh-blog-fe#375
- PR: pyo-sh/pyosh-blog-fe#385
- 상태: 머지 완료

### 작업 내용

- `src/shared/api/session-cleanup.ts`에 클라이언트 세션 cleanup callback registry와 admin auth-boundary failure helper를 추가했다.
- `QueryProvider`가 `queryClient.clear()`를 cleanup callback으로 등록하고, CSRF 모듈이 `clearCsrfToken()`을 같은 cleanup 경로에 등록하도록 연결했다.
- `/manage/login` 렌더링 시 cleanup을 실행해 middleware redirect, 직접 진입, forbidden redirect 후 login 렌더링 흐름에서 이전 admin cache/token promise를 정리하도록 했다.
- `clientFetch()`의 `/manage` 401/403 인증 경계 응답과 asset upload XHR 401/403 실패에서 cleanup 후 login redirect를 수행하도록 했다.
- 로그인 폼의 invalid credential 401은 기존 form error 흐름을 유지하도록 `/manage/login` route는 auth-boundary redirect에서 제외했다.
- #374 로그아웃 성공 흐름은 직접 `queryClient.clear()`/`clearCsrfToken()`을 호출하지 않고 공통 cleanup helper를 재사용하도록 정리했다.

### 검증

- `pnpm compile:types`
- `pnpm lint` (기존 unrelated warning 2건 유지)
- `pnpm build`
- 자동 리뷰: 3라운드, 최종 Critical 0, Warning 0, Suggestion 0

## #374 Admin 로그아웃 시 클라이언트 민감 캐시 정리

- Issue: pyo-sh/pyosh-blog-fe#374
- PR: pyo-sh/pyosh-blog-fe#384
- 상태: 머지 완료

### 작업 내용

- `AdminLogoutButton`에서 `/auth/admin/logout` 성공 후 React Query `queryClient.clear()`를 호출하도록 연결했다.
- 로그아웃 성공 후 module-level CSRF `tokenPromise`가 남지 않도록 `clearCsrfToken()`을 호출했다.
- 서버 로그아웃 실패 시에는 기존처럼 toast만 표시하고 클라이언트 cache/token 정리는 수행하지 않도록 성공 경로에만 정리를 배치했다.
- 정리 이후 기존 흐름대로 `/manage/login` 이동과 `router.refresh()`를 수행한다.

### 검증

- `pnpm compile:types`
- `pnpm lint` (기존 unrelated warning 2건 유지)
- `pnpm build`
- 자동 리뷰: Critical 0, Warning 0, Suggestion 0
