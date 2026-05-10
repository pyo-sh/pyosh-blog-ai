# Client Progress — 2026-05-10

## #381 Admin 에셋 카테고리와 썸네일 선택 UX

- Issue: pyo-sh/pyosh-blog-fe#381
- PR: pyo-sh/pyosh-blog-fe#391
- 상태: 머지 완료

### 작업 내용

- `src/entities/asset/*`에 `displayName`, `category`, category CRUD, category/search list params, 단일/일괄 metadata update, upload metadata payload 계약을 추가했다.
- 관리자 에셋 화면에서 업로드 기본 카테고리, 파일별 별명/카테고리 입력, 업로드 중 입력 잠금, 실패 후 metadata 유지 재시도 흐름을 추가했다.
- 에셋 목록에 카테고리 필터, 별명/파일명 검색, displayName 우선 카드 제목, 파일명 보조 표시, 카테고리 배지를 추가했다.
- 에셋 상세 모달에서 별명과 카테고리를 수정할 수 있게 하고, 별도 카테고리 관리 모달에서 사용자 카테고리 생성/이름 변경/삭제를 처리했다.
- 기본 카테고리 `썸네일`, `기본`, `미분류`는 보호 카테고리로 표시하고 삭제 액션을 노출하지 않도록 했다.
- 선택 모드 하단 액션에 여러 에셋 카테고리 일괄 변경을 추가했다.
- 썸네일 선택 `AssetPickerModal`에 카테고리 필터, 검색, 선택 요약, displayName 우선 표시, 현재 글 이미지 우선 정렬 옵션을 추가했다.
- 썸네일 직접 업로드는 `thumbnail` 기본 카테고리 metadata를 전송하고, 본문 이미지 업로드는 서버 기본 카테고리 계약을 사용하도록 유지했다.

### 검증

- `pnpm compile:types`
- `pnpm lint` (기존 unrelated warning 1건 유지: `src/shared/ui/error-boundary.tsx`)
- `pnpm build`
- 자동 리뷰: Critical 0, Warning 0, Suggestion 0

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
