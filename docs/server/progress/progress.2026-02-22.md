# Progress 2026-02-22

## ✅ 완료: E1. 최초 관리자 계정 생성 기능 삭제

### 작업 내용
- `POST /admin/setup` 라우트 핸들러 및 `AdminSetupSchema` 삭제
- `AdminService.createAdmin()`, `hasAnyAdmin()`, `AdminCreateArgs` 인터페이스 삭제
- 미사용 import (`sql`, `hashPassword`) 정리
- setup 관련 테스트 2건 삭제, admin 미존재 시 로그인 401 테스트 추가
- `api-spec.md`에서 setup 엔드포인트 명세 제거
- `server/scripts/hash-password.ts` Argon2id 기반 비밀번호 해시 스크립트 작성

### 수정/생성/삭제된 파일
- 수정: `server/src/routes/auth/auth.route.ts` (setup 핸들러 + 스키마 삭제)
- 수정: `server/src/routes/auth/admin.service.ts` (createAdmin, hasAnyAdmin 삭제)
- 수정: `server/test/routes/auth.test.ts` (setup 테스트 삭제, 401 테스트 추가)
- 수정: `docs/server/api-spec.md` (setup 명세 제거)
- 수정: `docs/server/tasks/task-01-remove-admin-setup.md` (체크박스 완료)
- 생성: `server/scripts/hash-password.ts`

### 검증 결과
- ✅ TypeScript 빌드 (`tsc --noEmit`) 에러 없음
- ✅ ESLint 0 errors, 0 warnings (변경 파일만)
- ⚠️ 테스트 실행: MySQL ECONNREFUSED (DB 미실행 환경 이슈)

### 다음 단계
- MySQL 실행 후 `pnpm test` 전체 테스트 통과 확인

---

## ✅ 완료: E5. user_tb, image_tb 삭제 (task-02)

### 작업 내용
- `passport.ts`: `userTable`/`imageTable` 완전 제거 → `oauthAccountTable` 기반으로 Google/GitHub OAuth 플로우 재작성 (providerUserId = profile.id 기반)
- `comment.service.ts`, `guestbook.service.ts`: 작성자 조회 쿼리를 `userTable` → `oauthAccountTable`로 교체, `name` → `displayName`/`avatarUrl` 사용
- `relations/comments.ts`, `relations/guestbook.ts`: Drizzle relation 수정 (`userTable` → `oauthAccountTable`)
- `types/fastify.d.ts`, `shared/interaction.ts`, `comment.route.ts`, `guestbook.route.ts`: `User` 타입 → `OAuthAccount`로 교체
- `routes/user/` 디렉토리 전체 삭제 (`user.route.ts`, `user.service.ts`, `user.schema.ts`)
- `app.ts`: UserService, createUserRoute 제거
- `swagger.ts`: "user" tag 제거
- `schema/users.ts`, `schema/images.ts` 삭제
- `schema/index.ts`: users/images export 제거
- `test/helpers/seed.ts`: `seedUser` → `seedOAuthUser` (`oauthAccountTable` 기반)
- `test/routes/guestbook.test.ts`, `test/routes/comments.test.ts`: `seedUser` → `seedOAuthUser`, `{ name:` → `{ displayName:` 교체
- Drizzle 마이그레이션 생성: `drizzle/0001_chubby_chamber.sql` (`DROP TABLE user_tb`, `DROP TABLE image_tb`)

### 수정/생성/삭제된 파일
- 삭제: `server/src/db/schema/users.ts`
- 삭제: `server/src/db/schema/images.ts`
- 삭제: `server/src/routes/user/user.route.ts`
- 삭제: `server/src/routes/user/user.service.ts`
- 삭제: `server/src/routes/user/user.schema.ts`
- 수정: `server/src/db/schema/index.ts`
- 수정: `server/src/db/relations/comments.ts`
- 수정: `server/src/db/relations/guestbook.ts`
- 수정: `server/src/plugins/passport.ts`
- 수정: `server/src/types/fastify.d.ts`
- 수정: `server/src/shared/interaction.ts`
- 수정: `server/src/routes/comments/comment.service.ts`
- 수정: `server/src/routes/comments/comment.route.ts`
- 수정: `server/src/routes/guestbook/guestbook.service.ts`
- 수정: `server/src/routes/guestbook/guestbook.route.ts`
- 수정: `server/src/app.ts`
- 수정: `server/src/plugins/swagger.ts`
- 수정: `server/test/helpers/seed.ts`
- 수정: `server/test/routes/guestbook.test.ts`
- 수정: `server/test/routes/comments.test.ts`
- 생성: `server/drizzle/0001_chubby_chamber.sql`

### 검증 결과
- ✅ TypeScript 빌드 (`tsc --noEmit`) 에러 없음
- ✅ Grep 재확인: `user_tb`/`image_tb`/`userTable`/`imageTable` 코드 참조 완전 제거
- ⚠️ 테스트 실행: DB 환경 필요 (MySQL 미실행)

### 다음 단계
- MySQL 실행 후 `pnpm drizzle-kit migrate` 실행하여 DB에 마이그레이션 적용
- `pnpm test` 전체 테스트 통과 확인

---

## ✅ 완료: E6 (task-03). oauth_account_tb 기반 /api/user 신규 구현

### 작업 내용

- T2: `oauth_account_tb`에 `deletedAt` (timestamp, nullable) 컬럼 추가
- T2: Drizzle 마이그레이션 `0002_add-deleted-at-to-oauth-account.sql` 생성 + DB 직접 적용
- T3: `user.service.ts` 작성 (getMyProfile / updateMyProfile / deleteMyAccount)
- T4: `user.schema.ts` 작성 (UpdateMyProfileBodySchema, UserProfileResponseSchema)
- T4: `user.route.ts` 작성 (GET/PUT/DELETE /api/user/me, requireAuth)
- `app.ts` UserService 인스턴스화 및 라우트 등록 (`/api/user` prefix)
- T6: `comment.service.ts` — 탈퇴 유저(deletedAt != null) 마스킹 ("탈퇴한 사용자")
- T6: `guestbook.service.ts` — 동일 마스킹 정책 적용
- T7: `test/routes/user.test.ts` 11 케이스 작성 및 전체 통과

### 수정/생성된 파일

- 수정: `server/src/db/schema/oauth-accounts.ts` (deletedAt 추가)
- 생성: `server/drizzle/0002_add-deleted-at-to-oauth-account.sql`
- 생성: `server/src/routes/user/user.schema.ts`
- 생성: `server/src/routes/user/user.service.ts`
- 생성: `server/src/routes/user/user.route.ts`
- 수정: `server/src/app.ts` (UserService/createUserRoute 등록)
- 수정: `server/src/routes/comments/comment.service.ts` (탈퇴 유저 마스킹)
- 수정: `server/src/routes/guestbook/guestbook.service.ts` (탈퇴 유저 마스킹)
- 생성: `server/test/routes/user.test.ts`

### 검증 결과

- ✅ TypeScript 빌드 (`tsc --noEmit`) 에러 없음
- ✅ 전체 테스트 통과: 58 tests (신규 11개 포함)

### 특이사항

- `drizzle-kit migrate` 실패: `__drizzle_migrations` 메타 테이블 동기화 이슈로 기존 마이그레이션 재실행 시도
  → Node.js/mysql2로 ALTER TABLE SQL 직접 실행하여 해결

---

## ✅ 완료: E2 (task-04). Post 썸네일 thumbnailUrl 전환

### 작업 내용

- `post_tb` 스키마를 `thumbnail_asset_id` → `thumbnail_url` 기반으로 전환
- Post/Asset relation 제거 (`server/src/db/relations/posts.ts`)
- Drizzle 마이그레이션 `0003_thin_boom_boom.sql` 생성
- 마이그레이션에 backfill SQL 추가:
  - `post_tb.thumbnail_asset_id`와 `asset_tb.id`를 조인
  - `thumbnail_url = CONCAT('/uploads/', storage_key)`로 이관
  - 이관 후 `thumbnail_asset_id` drop
- Posts API 요청/응답 스키마를 `thumbnailUrl`로 교체
  - `POST/PATCH /api/admin/posts`: `thumbnailUrl` 입력 지원
  - 빈 문자열 `null` 변환
  - `/uploads/...` 및 `http(s)` URL 허용, `javascript:` 차단
- PostService에서 asset 조인 제거 후 `thumbnailUrl` 직접 저장/반환
- API 문서(`docs/server/api-spec.md`) 예시 갱신
- Posts 라우트 테스트를 `thumbnailUrl` 케이스로 보강

### 수정/생성된 파일

- 수정: `server/src/db/schema/posts.ts`
- 수정: `server/src/db/relations/posts.ts`
- 생성/수정: `server/drizzle/0003_thin_boom_boom.sql`
- 생성: `server/drizzle/meta/0003_snapshot.json`
- 수정: `server/drizzle/meta/_journal.json`
- 수정: `server/src/routes/posts/post.schema.ts`
- 수정: `server/src/routes/posts/post.route.ts`
- 수정: `server/src/routes/posts/post.service.ts`
- 수정: `server/test/routes/posts.test.ts`
- 수정: `docs/server/api-spec.md`
- 수정: `docs/server/tasks/task-04-thumbnail-url-migration.md`

### 검증 결과

- ✅ TypeScript 빌드 (`pnpm compile:types`) 통과
- ⚠️ `pnpm test test/routes/posts.test.ts` 실행 실패 (sandbox DB 접근 `EPERM`)

### 코드 리뷰 피드백 반영 (추가 작업)

- `ThumbnailUrlInputSchema`: `z.preprocess` + `z.union` → `z.string().trim().nullable()` 단순화
- `thumbnailUrl` 컬럼: `text` → `varchar(500)` (schema + migration SQL + snapshot 동기화)
- `drizzle/meta/_journal.json` 파일 끝 개행 추가
- ✅ TypeScript 빌드 에러 없음, 전체 테스트 60개 통과

### 다음 단계

- `pnpm drizzle-kit migrate`로 `0003_thin_boom_boom.sql` 적용 (운영 DB)

---

## ✅ 완료: E4 (task-05). Tag API 제거 + Posts tagSlug 검색 전환

### 작업 내용

- Tag 독립 API 제거
  - `createTagRoute` 등록 제거 (`server/src/app.ts`)
  - `server/src/routes/tags/tag.route.ts` 삭제
  - `server/src/routes/tags/tag.schema.ts` 삭제
- TagService 정리
  - 유지: `getOrCreateTags()`, `deleteUnusedTags()`
  - 제거: `searchTags()`, `getAllTags()`
  - 태그 정규화 강화: trim + lowercase + empty 제거 + dedupe
- Posts 검색 파라미터 전환
  - `tagId` 제거, `tagSlug` 추가 (`post.schema.ts`)
  - `getPostList()`에서 `tagSlug`로 `tag_tb` 조회 후 `post_tag_tb` 필터링
- 테스트/문서 정리
  - Tag API 테스트 파일 삭제 (`server/test/routes/tags.test.ts`)
  - posts 테스트에 `GET /api/posts?tagSlug=...` 필터링 케이스 추가
  - posts 테스트에 `/api/tags` 404 케이스 추가
  - `docs/server/api-spec.md`에서 Tags 섹션 제거 및 posts query 문서를 `tagSlug`로 갱신

### 수정/삭제된 파일

- 수정: `server/src/app.ts`
- 수정: `server/src/routes/posts/post.schema.ts`
- 수정: `server/src/routes/posts/post.service.ts`
- 수정: `server/src/routes/tags/tag.service.ts`
- 수정: `server/test/routes/posts.test.ts`
- 수정: `docs/server/api-spec.md`
- 수정: `docs/server/tasks/task-05-remove-tag-api.md`
- 삭제: `server/src/routes/tags/tag.route.ts`
- 삭제: `server/src/routes/tags/tag.schema.ts`
- 삭제: `server/test/routes/tags.test.ts`

### 검증 결과

- ✅ TypeScript 빌드 (`pnpm compile:types`) 통과
- ⚠️ `pnpm test test/routes/posts.test.ts` 실행 실패 (sandbox DB 접근 `EPERM`)

### 다음 단계

- 로컬 DB 접근 가능한 환경에서 `pnpm test test/routes/posts.test.ts` 재실행
- `pnpm test` 전체 테스트 회귀 확인

---

## ✅ 완료: E3 (task-06). GET /api/categories/:slug 제거

### 작업 내용

- Categories Public 단건 조회 라우트 제거
  - `GET /api/categories/:slug` 핸들러 삭제
  - 라우트 스키마 import 정리 (`CategorySlugParamSchema`, `CategoryGetResponseSchema` 제거)
- CategoryService 정리
  - `getCategoryBySlug()` 메서드 삭제
  - 코드베이스 grep으로 해당 메서드 참조 제거 확인
- Categories 스키마 정리
  - `CategorySlugParamSchema`, `CategoryGetResponseSchema`, `CategorySlugParam` 타입 제거
- 테스트 보강
  - `server/test/routes/categories.test.ts`에 `/api/categories/:slug` 요청 시 404 검증 케이스 추가
- 문서 반영
  - `docs/server/api-spec.md`에서 `GET /api/categories/:slug` 명세 제거
  - 카테고리 조회는 `GET /api/categories` 트리 엔드포인트로 통합한다는 설명 추가
- 클라이언트 영향 확인
  - client 코드에서 `/api/categories/:slug` 호출 검색 결과 없음

### 수정된 파일

- 수정: `server/src/routes/categories/category.route.ts`
- 수정: `server/src/routes/categories/category.service.ts`
- 수정: `server/src/routes/categories/category.schema.ts`
- 수정: `server/test/routes/categories.test.ts`
- 수정: `docs/server/api-spec.md`
- 수정: `docs/server/tasks/task-06-remove-category-slug.md`
- 수정: `docs/server/progress.index.md`

### 검증 결과

- ✅ TypeScript 빌드 (`pnpm --dir server compile:types`) 통과
- ⚠️ `pnpm --dir server test test/routes/categories.test.ts` 실행 실패 (sandbox DB 접근 `EPERM`)

---

## ✅ 완료: Task 01. Rate Limiting & CSRF 보호

### 작업 내용
- `@fastify/rate-limit` v10.3.0 설치 및 플러그인 등록 (글로벌 100 req/min)
- 엔드포인트별 Rate Limit 세분화 (`config.rateLimit` 라우트 옵션)
  - `POST /api/auth/admin/login`: 5 req/min
  - `POST /api/posts/:postId/comments`: 10 req/min
  - `POST /api/guestbook`: 10 req/min
  - `POST /api/stats/view`: 30 req/min
- `@fastify/csrf-protection` v7.1.0 설치 및 세션 기반 플러그인 등록
- `GET /api/auth/csrf-token` 엔드포인트 신규 추가
- state-changing 엔드포인트에 `onRequest: fastify.csrfProtection` 적용
  - admin logout, POST comments, DELETE comments, POST guestbook, DELETE guestbook, POST stats/view
- 테스트 환경 분기: rate-limit 비활성화, csrfProtection no-op

### 의존성 추가
- `@fastify/rate-limit` v10.3.0
- `@fastify/csrf-protection` v7.1.0

### 수정/생성된 파일
- `src/plugins/rate-limit.ts` (신규)
- `src/plugins/csrf.ts` (신규)
- `src/app.ts` (플러그인 import + 등록 순서)
- `src/routes/auth/auth.route.ts` (csrf-token 엔드포인트 + admin/login rate limit + logout CSRF)
- `src/routes/comments/comment.route.ts` (POST rate limit + CSRF, DELETE CSRF)
- `src/routes/guestbook/guestbook.route.ts` (POST rate limit + CSRF, DELETE CSRF)
- `src/routes/stats/stats.route.ts` (POST rate limit + CSRF)
- `docs/server/findings/findings.013-rate-limiting-csrf.md` (신규)
- `docs/server/findings.index.md`, `docs/server/progress.index.md`, `docs/server/tasks/task-01-rate-limiting-csrf.md` 업데이트

### 검증 결과
- ✅ TypeScript 타입 체크 (`pnpm compile:types`) 통과
- ✅ 기존 테스트 60/60 통과 (`pnpm test`)
- ✅ 내가 수정한 파일들의 ESLint 오류 수정

### 성과
- 브루트포스 / 스팸 요청 방어 레이어 추가
- CSRF 공격 차단 인프라 구축 및 주요 엔드포인트 보호

### 다음 단계
- task-02 진행 예정

---

## ✅ 완료: Task 02. 게시글 검색 API (GET /api/posts?q=keyword)

### 작업 내용

- **검색 전략 결정**: MySQL LIKE 선택 (블로그 규모에 최적, 외부 서비스/FULLTEXT 불필요)
- `PostListQuerySchema`에 `q: z.string().min(1).max(200).optional()` 파라미터 추가
- `GetPostListQuery` 인터페이스에 `q?: string` 필드 추가
- `getPostList()` 메서드에 LIKE 검색 조건 추가 (title OR contentMd)
  - Drizzle `like()` + `or()` 함수 사용
  - 기존 categoryId, tagSlug, status, visibility 필터와 AND 조합
- 통합 테스트 3건 추가 (제목 매칭, 본문 매칭, 필터+검색 조합)
- findings.014 기술 선택 문서 작성

### 수정된 파일

- `server/src/routes/posts/post.schema.ts` (q 파라미터 추가)
- `server/src/routes/posts/post.service.ts` (like/or import + 검색 로직)
- `server/test/routes/posts.test.ts` (테스트 3건 추가)
- `docs/server/findings/findings.014-post-search-strategy.md` (신규)
- `docs/server/findings.index.md` (014 항목 추가)
- `docs/server/tasks/task-02-post-search-api.md` (체크박스 업데이트)

### 검증 결과

- ✅ 전체 테스트 19/19 통과 (`pnpm test test/routes/posts.test.ts`)
- ✅ q 파라미터 미전달 시 기존 목록 조회 동작 유지

---

## ✅ 완료: Task 03. 관리자 댓글/방명록 관리 API

### 작업 내용

- `AdminCommentListQuerySchema` / `AdminCommentListResponseSchema` / `AdminCommentItemSchema` 추가 (`comment.schema.ts`)
- `AdminGuestbookListQuerySchema` / `AdminGuestbookListResponseSchema` / `AdminGuestbookItemSchema` 추가 (`guestbook.schema.ts`)
- `CommentService.getAdminComments()` 메서드 추가 (page, limit, postId, authorType, startDate, endDate 필터 + 비밀글 마스킹 없음)
- `GuestbookService.getAdminGuestbook()` 메서드 추가 (page, limit, authorType, startDate, endDate 필터 + 비밀글 마스킹 없음)
- `GET /api/admin/comments` 라우트 추가 (`createAdminCommentRoute` 내)
- `GET /api/admin/guestbook` 라우트 추가 (`createAdminGuestbookRoute` 내)
- 통합 테스트 8건 추가 (댓글 4건 + 방명록 4건)

### 수정된 파일

- `server/src/routes/comments/comment.schema.ts`
- `server/src/routes/comments/comment.service.ts`
- `server/src/routes/comments/comment.route.ts`
- `server/src/routes/guestbook/guestbook.schema.ts`
- `server/src/routes/guestbook/guestbook.service.ts`
- `server/src/routes/guestbook/guestbook.route.ts`
- `server/test/routes/comments.test.ts` (테스트 4건 추가)
- `server/test/routes/guestbook.test.ts` (테스트 4건 추가)
- `docs/server/tasks/task-03-admin-comments-guestbook.md` (체크박스 업데이트)

### 검증 결과

- ✅ TypeScript 빌드 (`pnpm tsc --noEmit`) 통과 (0 errors)
- ✅ 전체 테스트 71/71 통과 (`pnpm test`)

### 성과

- 관리자가 전체 댓글/방명록을 페이지네이션+필터로 조회 가능
- 비밀글도 원문 반환 (관리자 권한 필요 기능)
- `DELETE /api/admin/comments/:id`, `DELETE /api/admin/guestbook/:id`도 기존에 완성되어 있어 task-03 전체 완료
