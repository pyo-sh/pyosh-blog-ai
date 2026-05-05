# Client Progress — 2026-05-05

## #379 검색엔진 노출 토글 및 noindex 메타 처리

- Issue: pyo-sh/pyosh-blog-fe#379
- PR: pyo-sh/pyosh-blog-fe#389
- 상태: 머지 완료

### 작업 내용

- Post 모델과 create/update payload에 `searchIndexable`을 추가하고, API normalize 단계에서 기존 응답 누락 시 기본값을 `true`로 보정했다.
- Post editor 기본값을 `searchIndexable=true`로 두고, 서버 초기값 hydration과 저장 payload에 검색엔진 노출 값을 포함했다.
- 작성/수정 form, 글 목록 card preview, Admin preview control bar에 검색엔진 노출 상태를 표시하고 토글을 추가했다.
- Admin 글 목록에 검색엔진 노출 상태 column과 optimistic quick toggle을 추가했다.
- `visibility=private` 글에서는 검색엔진 토글을 비활성화하고 “검색 제외” 상태로 표시하되, 저장된 `searchIndexable` 값은 유지해 public 전환 시 이전 의도가 보존되도록 했다.
- 공개 글 상세 metadata에서 `searchIndexable=false`이면 `robots: { index: false, follow: true }`를 추가하고, canonical/Open Graph/Twitter metadata는 유지했다.
- `searchIndexable=false` 글 상세에서는 `BlogPosting` JSON-LD를 렌더링하지 않도록 했다.
- `PublishedPostSlug.searchIndexable`을 sitemap slug contract에 포함하고, sitemap은 `searchIndexable=true` slug만 emit하도록 보정했다.
- 관련 Storybook mock과 story initial data에 `searchIndexable`을 추가했다.

### 검증

- `pnpm compile:types`
- `pnpm lint` (기존 unrelated warning 2건 유지)
- `pnpm build`
- 자동 리뷰: 3라운드 후 Critical 0, Warning 0, Suggestion 0
- 참고: `pnpm exec tsc -p tsconfig.storybook.json --noEmit`은 기존 Storybook `Post` mock과 `PublishedPostListItem` 타입 불일치가 남아 실패했다.

## #378 Admin 글 수정 페이지 초기 데이터 서버 주입

- Issue: pyo-sh/pyosh-blog-fe#378
- PR: pyo-sh/pyosh-blog-fe#388
- 상태: 머지 완료

### 작업 내용

- `/manage/posts/[id]/edit` route를 Client Component에서 `force-dynamic` Server Component로 전환해 글 상세 초기 데이터를 서버 렌더 단계에서 준비하도록 했다.
- `cookies()`에서 `sessionId`만 읽어 내부 Admin API 호출용 cookie header를 만들고, 클라이언트 prop으로 인증 정보를 전달하지 않도록 했다.
- Admin 상세 fetch는 기존 `serverFetch` 기본 `cache: "no-store"` 경로를 사용해 public cache helper나 revalidate 옵션을 타지 않게 유지했다.
- 잘못된 ID와 404는 `notFound()`로 처리하고, 401/403은 `/manage/login` 또는 `/manage/login?reason=forbidden`으로 redirect하도록 정리했다.
- `PostDetail -> PostFormValues` 변환 로직을 post-editor의 순수 helper로 분리하고 edit page와 저장 성공 후 form hydration에서 재사용했다.
- preview page도 동일한 Admin post cookie header helper를 사용하도록 중복을 줄였다.

### 검증

- `pnpm compile:types`
- `pnpm lint` (기존 unrelated warning 2건 유지)
- `pnpm build`
- 자동 리뷰: Critical 0, Warning 0, Suggestion 1(public API import 반영 후 skip-review merge)

## #377 Public 서버 fetch 및 cache 정책 최적화

- Issue: pyo-sh/pyosh-blog-fe#377
- PR: pyo-sh/pyosh-blog-fe#387
- 상태: 머지 완료

### 작업 내용

- `serverFetch`가 별도 cache 옵션이 없을 때만 `cache: "no-store"`를 기본 적용하도록 정리하고, 공개 데이터 전용 `publicServerFetch` helper를 추가했다.
- 공개 데이터 revalidate 기준을 `PUBLIC_CACHE_REVALIDATE_SECONDS`로 모아 글 목록/상세, taxonomy, 통계, sitemap 계열 fetch에 시간 기반 revalidate를 명시했다.
- `fetchPosts`, `fetchPostBySlug`, `fetchPublishedPostSlugs`, `fetchCategories`, `fetchTags`, `fetchPopularPosts`, `fetchTotalViews`를 public cache helper 기반으로 전환했다.
- Admin/auth/comment/guestbook 등 인증 또는 사용자별 표시가 섞일 수 있는 fetch는 기존 `serverFetch` 경로를 유지해 `no-store` 기본값을 계속 사용하도록 했다.
- RSS와 sitemap은 public fetch revalidate를 사용하되 `next build` 시 API 서버를 요구하지 않도록 dynamic route로 유지했다.

### 검증

- `pnpm compile:types`
- `pnpm lint` (기존 unrelated warning 2건 유지)
- `pnpm build`
- 자동 리뷰: Critical 0, Warning 0, Suggestion 0

## #376 Client 데이터 로딩 및 query key 정책 표준화

- Issue: pyo-sh/pyosh-blog-fe#376
- PR: pyo-sh/pyosh-blog-fe#386
- 상태: 머지 완료

### 작업 내용

- `src/entities/*/query-keys.ts`에 public/admin namespace가 분리된 query key factory를 추가했다.
- 관리자 글 목록/detail/pinned count, 관리자 카테고리 tree, 관리자 에셋 list, 관리자 댓글 list/recent dashboard, 관리자 방명록 list/settings, dashboard stats key를 공유 factory 기반으로 교체했다.
- public 글 목록과 public tag list key도 factory를 사용하도록 정리해 admin hidden 데이터 key와 공개 데이터 key가 root부터 섞이지 않도록 했다.
- 카테고리/방명록처럼 admin mutation이 public 화면에도 영향을 주는 경우에는 admin/public key를 각각 명시적으로 갱신하도록 분리했다.
- Post editor 태그 제안은 `publicTagKeys.list()`를 사용하되 input focus 또는 입력 이후에만 `/tags`를 조회하도록 지연했다.
- 객체형 query key params는 factory 내부에서 고정된 property 순서로 정규화하도록 했다.

### 검증

- `pnpm compile:types`
- `pnpm lint` (기존 unrelated warning 2건 유지)
- `pnpm build`
- 자동 리뷰: Critical 0, Warning 0, Suggestion 0
