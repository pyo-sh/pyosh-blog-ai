# Client Progress — 2026-05-10

## #380 Admin middleware 관리자 세션 검증 강화

- Issue: pyo-sh/pyosh-blog-fe#380
- PR: pyo-sh/pyosh-blog-fe#390
- 상태: 머지 완료

### 작업 내용

- `src/middleware.ts`의 `/manage` 보호 로직을 `response.ok` 기반 인증 확인에서 `ManageAuthState` 기반 관리자 권한 확인으로 교체했다.
- `/auth/me`가 200을 반환해도 JSON body의 `type`이 `"admin"`인 경우에만 `/manage` 접근을 허용하도록 했다.
- 401은 `anonymous`, 403 또는 admin이 아닌 응답은 `non_admin`, timeout/5xx/invalid JSON/API_URL 누락은 `unavailable`로 분리했다.
- `/manage/login`은 admin 세션만 `/manage`로 redirect하고, OAuth 등 non-admin 세션은 login page에 머물 수 있도록 했다.
- 보호된 `/manage` route에서 non-admin은 `reason=admin_required`, auth 확인 장애는 `reason=auth_unavailable`을 붙여 login으로 fail closed 처리했다.
- 기존 CSP nonce, `Content-Security-Policy-Report-Only`, non-production `X-Robots-Tag`, matcher 흐름은 유지했다.

### 검증

- `pnpm compile:types`
- `pnpm lint` (기존 unrelated warning 2건 유지)
- `pnpm build`
- 자동 리뷰: Critical 0, Warning 0, Suggestion 0
