# Server Progress - 2026-03-26

## Issue #39 - Production security settings (PR #57)

**Status**: Merged

### What was done

Implemented production security hardening across five plugin files and one route file.

- `session.ts`: added `httpOnly: true`, `path: '/'`, `sameSite: 'lax'` (uniform across environments; `strict` avoided because OAuth provider redirects would drop the cookie on a cross-site navigation), `secure` bound to `NODE_ENV === 'production'`
- `cors.ts`: added explicit `methods`, `allowedHeaders` (including `X-CSRF-Token`), and `maxAge` (7200 in production, 0 in development)
- `helmet.ts`: set `contentSecurityPolicy: false` - CSP responsibility delegated to Next.js client; removed unused `NodeEnv` import
- `swagger.ts`: early return when `NODE_ENV === 'production'` so `/docs` is not registered in production
- `app.ts`: consolidated all `/api/admin/*` routes into a single sub-plugin with an `onRequest` hook that calls `csrfProtection` for any method not in `{GET, HEAD, OPTIONS, TRACE}`; sub-prefixes within the admin plugin mirror the original `/api/admin` structure
- `asset.route.ts`: added `onRequest: fastify.csrfProtection` to `POST /api/assets/upload`

### Review notes

Round 2 raised a critical issue: `sameSite: 'strict'` breaks OAuth callbacks because browsers withhold strict-samesite cookies on cross-site redirects from OAuth providers. Fixed by using `'lax'` uniformly. Round 1 raised that the CSRF hook should use a safe-methods set (`GET, HEAD, OPTIONS, TRACE`) rather than only excluding `GET`.

## Issue #38 - User API (PR #58)

**Status**: Merged

### What was done

Implemented OAuth user profile management endpoints under `/api/user/me`, all protected by the `requireAuth` preHandler hook. The implementation was already on `main` from earlier migration work; this PR formalised it through the pipeline and fixed lint issues.

**Files:**
- `src/routes/user/user.route.ts` - GET/PUT/DELETE `/me` handlers with `requireAuth`; PUT body uses `fastify-type-provider-zod`-validated `request.body` directly (no redundant re-parse); 404 added to all response schemas for OpenAPI completeness
- `src/routes/user/user.service.ts` - `UserService`: `getMyProfile`, `updateMyProfile` (partial update, supports `avatarUrl: null`), `deleteMyAccount` (soft delete: sets `deletedAt`), `isActive` (internal util)
- `src/routes/user/user.schema.ts` - `UpdateMyProfileBodySchema` (displayName 1-100, avatarUrl URL or null, both optional), `UserProfileResponseSchema` (excludes providerUserId and deletedAt)
- `test/routes/user.test.ts` - Integration tests: GET/PUT/DELETE happy paths, 401 on unauthenticated, avatarUrl null removal, empty body no-op, session destroyed after DELETE, deleted-user comment/guestbook masking

Deleted-user data retention: `comment.service.ts` and `guestbook.service.ts` already masked deleted OAuth accounts as "탈퇴한 사용자" (author id and avatarUrl omitted).

### Key design decisions

- Soft delete only: `deletedAt` is set; no rows are removed. Comments and guestbook entries are preserved and displayed with author "탈퇴한 사용자"
- Session destroyed synchronously after soft delete via `request.session.destroy()` - same request, no async gap
- `UserProfileResponseSchema` explicitly excludes `providerUserId` and `deletedAt` to avoid leaking sensitive/internal fields
- PUT handler skips the Drizzle UPDATE entirely when `updateData` is empty (no-op path returns existing row immediately)

### Review outcome

1 round. 0 critical, 0 warning, 2 suggestions. Suggestions applied (removed redundant `UpdateMyProfileBodySchema.parse(request.body)` in PUT handler; added 404 to GET/PUT/DELETE response schemas). Merged without re-review.

## Issue #33 - Assets API (PR #56)

**Status**: Merged

### What was done

Implemented the full Assets API (5 endpoints) with local file storage, image dimension extraction, and multipart upload support.

**New files:**
- `src/services/file-storage.service.ts` - `FileStorageService`: `bufferFile()` static helper (streams multipart file to Buffer inline, catches `FST_REQ_FILE_TOO_LARGE`), `saveFile(buffered)` (MIME type + size validation, UUID filename, date-based dir `uploads/YYYY/MM/`, `image-size` sync extraction for width/height), `deleteFile()` (idempotent ENOENT-tolerant), `getFilePath()` (path traversal guard via `..` check), `ensureUploadDir()`
- `src/routes/assets/asset.schema.ts` - Zod schemas: `assetResponseSchema`, `assetListItemSchema`, `uploadAssetsResponseSchema`, `assetListQuerySchema`, `assetIdParamSchema`, `bulkDeleteAssetsBodySchema` (`ids` array min 1 max 100), `errorResponseSchema`
- `src/routes/assets/asset.service.ts` - `AssetService`: `uploadAsset(buffered)`, `uploadAssets(buffered[])`, `getAssetById(id)`, `getAssetList(query)` with pagination, `deleteAsset(id)` (DB + file), `deleteAssets(ids)` (single transaction DB delete + `Promise.all` best-effort file cleanup)
- `src/routes/assets/asset.route.ts` - 5 routes registered with proper ordering; multipart files buffered in-loop via `FileStorageService.bufferFile()` before service call
- `test/routes/assets.test.ts` - 16 integration tests covering all endpoints

**Modified files:**
- `src/errors/http-error.ts` - added `payloadTooLarge()` static factory
- `package.json` / `pnpm-lock.yaml` - added `image-size ^2.0.2`
- `test/helpers/seed.ts` - added `seedAsset()` helper

### Key design decisions

- Multipart stream must be consumed inside the `for await` loop - deferring `toBuffer()` to the service caused the stream to hang. `FileStorageService.bufferFile()` is the designated consume-and-buffer point
- `@fastify/multipart` v9 throws `FST_REQ_FILE_TOO_LARGE` (FastifyError) when file exceeds `limits.fileSize`; caught in `bufferFile()` and re-thrown as `HttpError.payloadTooLarge(413)`
- `deleteAssets` uses `Promise.all` (not `allSettled`) with an inner try/catch - the inner catch swallows every error, so the two are not redundant at the behavior level but `allSettled` added no value
- `ids` array capped at 100 to prevent unbounded `WHERE id IN (...)` clauses; larger batches require server-side loops
- `image-size` v2 has no async Buffer API - sync call is the only option; acceptable at 10 MB limit

### Review outcome

2 rounds. Round 1: 0 critical, 1 warning, 1 suggestion. Warning: `bulkDeleteAssetsBodySchema` had no upper bound on `ids` - added `.max(100)`. Round 2: 0 critical, 0 warning, 2 suggestions. Both suggestions were no-change items (imageSize has no async Buffer API; allSettled refactored to Promise.all). Merged without re-review.

## Issue #34 - Categories API (PR #52)

**Status**: Merged

### What was done

Implemented the full Categories API (5 endpoints) with post count aggregation, batch tree update, and category delete with post migration actions.

**New files:**
- `src/routes/categories/category.schema.ts` - added `CategoryDeleteQuerySchema` (action enum + moveTo refinement), `CategoryTreeUpdateBodySchema` (changes array min 1/max 200), `publishedPostCount`/`totalPostCount` in all response schemas, `CategoryTreeResponse` type with children
- `src/routes/categories/category.service.ts` - `CategoryWithCounts` interface, `getAllCategoriesTree` with single GROUP BY post count query, `updateCategoryTree` with in-memory target-state cycle detection + FOR SHARE locking inside transaction, `deleteCategory` with action=move/trash handling both live and soft-deleted posts
- `src/routes/categories/category.route.ts` - 5 routes: GET `/`, POST `/`, PATCH `/tree` (before `/:id`), PATCH `/:id`, DELETE `/:id`; conditional Cache-Control on GET based on includeHidden flag

**Schema/migration changes:**
- `src/db/schema/posts.ts` - `categoryId` made nullable (removed `.notNull()`)
- `drizzle/0005_post_nullable_category.sql` - `ALTER TABLE post_tb MODIFY COLUMN category_id int`
- `drizzle/meta/0005_snapshot.json` - new snapshot with proper UUID chain
- `drizzle/meta/0004_snapshot.json` - fixed snapshot ID from string to UUID format

**Tests added (`test/routes/categories.test.ts`):**
- GET: empty list, tree structure, publishedPostCount/totalPostCount, slug-path removed (404)
- POST: admin create 201 with counts, unauthenticated 403
- PATCH /:id: name update
- PATCH /tree: batch reorder, 403, direct cycle 400, parent-child swap 200, self-parent 400
- DELETE: child exists 409, empty category 204, action=trash DB verification (deletedAt + null categoryId), action=move DB verification (categoryId = target), moveTo missing 400, action missing 400, moveTo===id 400, moveTo not found 400

### Key design decisions

- Cycle detection uses target-state map (batch changes applied before walking) so valid parent-child position swaps are allowed - DB-state approach falsely rejects them
- `allCategories` fetched inside transaction with `FOR SHARE` to close TOCTOU window between existence check and UPDATE batch
- `categoryId` made nullable to handle orphaned FK references when deleting categories
- `action=move`: live posts moved to target; already-soft-deleted posts get `categoryId = null` (not moved to target - preserves semantic that deleted posts are uncategorized)
- `action=trash`: all posts (live and already-deleted) get `deletedAt = sql\`NOW()\`` and `categoryId = null`
- `Cache-Control: no-store` when `include_hidden=true`; `public, max-age=300` for public responses
- PATCH `/tree` registered before PATCH `/:id` to prevent static path being captured as id

### Review outcome

12 rounds (11 standard + 1 suggestion-only skip). Final state: 0 critical, 0 warning, 0 suggestion. See [findings.016-categories-api.md](../findings/findings.016-categories-api.md).

## Issue #36 - Tags API (PR #55)

**Status**: Merged

### What was done

`GET /api/tags` was already fully implemented on `main` from PR #18 (issue #14). All 5 acceptance criteria were already met:

- Route handler in `src/routes/tags/tag.route.ts`
- `TagService.getPublicTagsWithCount()` in `src/routes/tags/tag.service.ts` - filters by `status=published`, `visibility=public`, `deletedAt IS NULL` via innerJoin; excludes tags with postCount=0 implicitly
- Zod schemas in `src/routes/tags/tag.schema.ts`
- Route registered at `/api/tags` in `src/app.ts`
- 2 integration tests in `test/routes/tags.test.ts`

Added one missing test case: empty database returns `{ tags: [] }`.

### Review outcome

Clean (0 critical, 0 warning, 0 suggestion). Approved and auto-merged.

## Issue #37 - Posts public API (PR #54)

**Status**: Merged

### What was done

Implemented the 3 public post endpoints, `PostDetail`/`PostListItem` response schemas with aggregates and category ancestors, and the `filter` search parameter.

**New endpoint:**
- `GET /api/posts/slugs` - returns `{ slugs: [{slug, updatedAt}] }` for published+public posts (sitemap use); capped at 50,000 rows with TODO for cursor pagination

**Schema changes (`post.schema.ts`):**
- `PostListItemSchema` - new schema for list responses: all `PostDetail` fields except `contentMd`, category without `ancestors`
- `PostDetailSchema` - extended with `totalPageviews: number`, `commentCount: number`, `category.ancestors: [{name, slug}]`
- `PostDetailCategorySchema` - `PostCategorySchema` + `ancestors` array (PostDetail only)
- `PostSlugsResponseSchema` - `{ slugs: [{slug, updatedAt}] }`
- `PostListResponseSchema` - updated to use `PostListItemSchema` (was `PostDetailSchema`)
- `PostListQuerySchema` - added `filter` enum: `title_content | title | content | tag | category | comment` (default `title_content`)

**Service changes (`post.service.ts`):**
- `enrichPostListItems(posts)` - batch method: 4 parallel queries (category IN, tags JOIN IN, stats SUM GROUP BY, comments COUNT GROUP BY) for N posts; replaces N×4 per-post calls
- `enrichPostWithDetails(post)` - single-post enrichment with stats, commentCount, category.ancestors; explicit null guard for missing category
- `fetchCategoryAncestors(categoryId, db)` - walks parentId chain with per-level queries; cycle-safe via `visited` Set; depth-capped at `MAX_DEPTH=10`
- `getPostSlugs()` - returns published+public slugs ordered by updatedAt desc, limited to 50,000
- `getPostList()` filter support - `title`/`content`/`title_content` use LIKE conditions; `tag` fetches matching tag IDs then post IDs; `category` fetches matching category IDs; `comment` fetches post IDs from comment body matches; else branch falls back to `title_content` when `filter` is undefined (direct service callers)
- `getPostByIdInternal()` - updated to include stats, commentCount, ancestors; explicit null guard for category

**Route changes (`post.route.ts`):**
- `GET /api/posts/slugs` registered before `GET /api/posts/:slug` to avoid route conflict

**Tests added (`test/routes/posts.test.ts`):**
- `GET /api/posts/slugs` - returns only published+public slugs; empty result when none
- `filter=tag` - match by tag name, empty result path
- `filter=category` - match by category name, empty result path
- `filter=comment` - match by comment body, empty result path
- `filter=title` / `filter=content` - field-scoped search
- `category.ancestors` - nested category returns parent in ancestors array
- `totalPageviews`/`commentCount` fields present in list response

### Key design decisions

- List endpoint uses 4 fixed queries regardless of page size (`enrichPostListItems`), not N×4 per post
- `PostListItem` excludes `contentMd` from list responses; `PostDetail` (single post) includes it
- `category.ancestors` only in `PostDetail`; list items use flat `PostCategorySchema` (no ancestors) for efficiency
- `fetchCategoryAncestors` avoids full-table scan by walking parentId chain individually; MAX_DEPTH=10 bounds worst-case depth traversal
- `filter` default enforced at Zod schema level; service has else fallback for direct callers

### Review outcome

5 rounds. Round 1: N+1 amplified to 4N (critical) - fixed with batch `enrichPostListItems`. Cycle guard missing (warning) - fixed with visited Set. Full category table scan (warning) - fixed with per-level parent chain walk. Round 2: MAX_DEPTH guard, tests for tag/category/comment filter modes, TODO for unbounded slugs. Round 3: else fallback for undefined filter, `.limit(50000)` on slugs. Round 4: null guard for category in single-post paths. Round 5: `HttpError.notFound` consistency in list batch path.

## Issue #35 - Guestbook + settings API (PR #53)

**Status**: Merged

### What was done

Implemented the full guestbook public/admin API (8 endpoints) and site settings API (2 endpoints).

**New files:**
- `src/db/schema/settings.ts` - `site_settings_tb` singleton table (`id=1`, `guestbook_enabled boolean`)
- `drizzle/0005_site_settings.sql` - migration creating the table + seeding the default row
- `src/routes/settings/settings.schema.ts` - `GuestbookSettingsResponseSchema`, `UpdateGuestbookSettingsBodySchema`
- `src/routes/settings/settings.service.ts` - `SettingsService` with `getGuestbookEnabled` / `setGuestbookEnabled` (upsert pattern)
- `src/routes/settings/settings.route.ts` - `GET /api/settings/guestbook` (public), `PATCH /api/admin/settings/guestbook` (admin)

**Modified files:**
- `src/db/schema/index.ts` - re-exported settings schema
- `src/routes/guestbook/guestbook.schema.ts` - added admin schemas: `AdminGuestbookDeleteQuerySchema` (`soft_delete|hard_delete`), `AdminGuestbookPatchQuerySchema` (`hide|restore`), `AdminGuestbookBulkDeleteBodySchema`, `AdminGuestbookBulkPatchBodySchema` (max 100 ids); fixed `AdminGuestbookItemSchema` status to include `"hidden"`; added `status` and `q` to `AdminGuestbookListQuerySchema`
- `src/routes/guestbook/guestbook.service.ts` - added `adminDeleteEntry`, `adminPatchEntry`, `bulkDeleteEntries`, `bulkPatchEntries`; updated `getAdminGuestbook` with status filter, LIKE search (metachar-escaped), date range
- `src/routes/guestbook/guestbook.route.ts` - added guestbook-enabled check on POST, added admin single/bulk PATCH (hide/restore) and DELETE (soft_delete/hard_delete) routes
- `src/app.ts` - registered settings routes, wired `settingsService` into guestbook route

### Key design decisions

- DELETE endpoints handle only irreversible actions (soft_delete, hard_delete); PATCH handles reversible state changes (hide, restore) - applied to both single and bulk routes
- All state transitions include source-status guards: hide only from `active`, restore only from `hidden`, soft_delete skips already-deleted rows to preserve original `deletedAt`
- Settings upsert uses Drizzle `onDuplicateKeyUpdate` with typed values (not deprecated `VALUES()` SQL syntax)
- LIKE metacharacters (`%`, `_`, `\`) escaped in search queries

### Review outcome

6 rounds. Key corrections: HTTP method separation for reversible/irreversible actions, restore narrowed to `hidden`-only (not undoing soft_delete), `hide` guard against overwriting `deleted` status, soft_delete idempotency to preserve audit trail `deletedAt`. Round 6 warnings fixed and merged without re-review (round limit).

See [findings.015-guestbook-settings-api.md](../findings/findings.015-guestbook-settings-api.md).

## Issue #32 - Logging and error management (PR #50)

**Status**: Merged

### What was done

Implemented Pino logging configuration per environment, sensitive data masking for request body, and production multistream output.

- Added `pino ^10.3.0` as a direct dependency (was previously only available as a transitive dep via fastify)
- `src/plugins/logger.ts`:
  - `buildFastifyLoggerConfig()` - env-aware Fastify constructor config: returns `loggerInstance` in prod, `logger` options in dev/test
  - `buildProdLoggerInstance()` - creates pino logger with multistream: stdout (info+) + `logs/error.log` (error only via `LOG_FILE` env var or `process.cwd()/logs/error.log`); `mkdirSync` creates the logs dir before `pino.destination()`; `process.once('exit')` flush handler to avoid async buffer loss
  - `REQ_SERIALIZER` - custom req serializer that explicitly excludes request body (protects password, guestPassword, guestEmail fields)
  - `REDACT_PATHS` - shared constant for header masking (authorization, cookie, set-cookie) used by both dev/prod options
  - `FastifyLoggerConfig` discriminated union type - ensures `logger | loggerInstance` is always present, catches future regressions at compile time
  - `disableRequestLogging: true` added for test env
  - `buildLoggerOptions()` unexported (internal detail, `buildFastifyLoggerConfig` is the public API)
- `src/app.ts`: spread `buildFastifyLoggerConfig()` into Fastify constructor

Existing implementations that were already correct (no changes needed):
- Global error handler: 500 errors log stack trace + request context, response body is "An unexpected error occurred"
- `HttpError` classification (400/401/403/404/409/413/429/500)
- Health endpoints (`/health`, `/api/health/live`, `/api/health/ready`)
- `logs/` directory in `.gitignore`

### Review outcome

Round 1: 1 critical, 2 warning, 1 suggestion. Critical: `logs/` dir not created - ENOENT crash at prod startup. Warning 1: relative log path fragile in containers. Warning 2: async pino.destination buffer loss on crash. All fixed.

Round 2: 0 critical, 0 warning, 2 suggestion. Suggestion 1: `process.once` instead of `process.on`. Suggestion 2: discriminated union return type. Both applied and merged without re-review.

## Issue #29 - DB schema + migrations (PR #49)

**Status**: Merged

### What was done

Completed the Drizzle ORM schema definition for all active tables and brought `post_tb` in line with the spec.

- 11 tables defined in `src/db/schema/`: `admin_tb`, `oauth_account_tb`, `session_tb`, `asset_tb`, `category_tb`, `tag_tb`, `post_tb`, `post_tag_tb`, `comment_tb`, `guestbook_entry_tb`, `stats_daily_tb`
- `user_tb` and `image_tb` were created in migration 0000 and dropped in migration 0001 - intentionally absent from the Drizzle schema code
- Added 5 missing `post_tb` columns: `summary varchar(200)`, `description varchar(300)`, `comment_status enum('open','locked','disabled')`, `is_pinned boolean`, `content_modified_at timestamp`
- Created `drizzle/0004_post_tb_extend.sql` with ALTER TABLE statements for all 5 columns
- Updated `drizzle/meta/_journal.json` and created `drizzle/meta/0004_snapshot.json`
- Updated Zod schemas: `CreatePostBodySchema`, `UpdatePostBodySchema`, `PostDetailSchema`
- Updated `CreatePostInput` and `UpdatePostInput` service interfaces
- Added `contentModifiedAt` auto-tracking in `updatePost` - set to `new Date()` when `contentMd` is changed
- Applied `.min(1)` validation to `summary`/`description` in both create and update schemas

### Review outcome

Round 1: 0 critical, 1 warning, 1 suggestion. Warning: `contentModifiedAt` had no write path. Applied automatic tracking on `contentMd` change. Added `.min(1)` to create-side `summary`/`description`.

Round 2: 0 critical, 0 warning, 1 suggestion. Suggestion: `UpdatePostBodySchema` missing `.min(1)` for `summary`/`description`. Applied and merged without re-review.

## Issue #30 - App bootstrap + health check (PR #47)

**Status**: Merged

### What was done

All acceptance criteria for issue #30 were already implemented on `main` from prior development:

- Fastify 5 instance with `ZodTypeProvider`
- Plugin registration in order: logger, helmet, rate-limit, drizzle, session, csrf, passport, multipart, static, swagger, cors
- Global error handler: `HttpError` → status/error/message, validation errors → 400, unhandled → 500 with safe message
- Health endpoints: `GET /health`, `GET /api/health`, `GET /api/health/live`, `GET /api/health/ready`
- Per-route rate limits: admin login (5/min), comments (10/min), guestbook (10/min), stats view (30/min)

### Fix applied

`GET /api/health` was missing `memory` field that the test at `test/routes/health.test.ts:74` expects.

Added `memory: getMemoryUsage()` to the `/api/health` response in `src/app.ts` to align implementation with test expectation.

### Review outcome

Clean (0 critical, 0 warning, 0 suggestion).

## Issue #31 - Auth system (PR #51)

**Status**: Merged

### What was done

Most of the auth system (routes, services, hooks, type declarations) was already present on `main` from prior development. This PR completed the remaining requirements:

- `src/shared/env.ts`: Made `GOOGLE_CLIENT_ID/SECRET` and `GITHUB_CLIENT_ID/SECRET` optional (changed from `z.string().min(1)` to `z.string().default("")`) - server can now start without OAuth credentials configured
- `src/plugins/passport.ts`: Google and GitHub strategies now registered conditionally only when both credential env vars are non-empty
- `src/routes/auth/auth.route.ts`: Google and GitHub OAuth routes (`/google`, `/google/callback`, `/github`, `/github/callback`) now registered conditionally - routes are absent when credentials are not configured
- `src/hooks/auth.hook.ts`: `optionalAuth` hook now explicitly sets `request.user = null` when unauthenticated (previously left it `undefined`)
- `src/types/fastify.d.ts`: Widened `FastifyRequest.user` type to `OAuthAccount | null` to reflect `optionalAuth` behavior

All 13 acceptance criteria passed. 7/7 auth integration tests green.

### Review outcome

Clean (0 critical, 0 warning, 0 suggestion). Approved and auto-merged.

## Issue #28 - Environment variable configuration (PR #48)

**Status**: Merged

### What was done

`shared/env.ts` and `shared/env-loader.ts` were already implemented with Zod validation and the correct env file loading order (`.env` → `.env.{ENV_TARGET}.local`, `.env.test` for test). The remaining work:

- Added `Object.freeze()` to the exported `env` object in `shared/env.ts` - satisfies the frozen object requirement
- Deleted legacy `src/constants/env.ts` (0 external imports; replaced by `shared/env.ts`)
- `src/constants/node-env.ts` kept - used by 4 plugins for `NodeEnv` enum comparisons
- Updated `.env.example`: required variables with example values, optional variables (`NODE_ENV`, `CLIENT_PORT`, `BASE_URL`, `BLOG_TITLE`, `BLOG_DESCRIPTION`) shown as comments

Docker Compose `env_file: ../../.env` was already in place.

### Review outcome

Clean (0 critical, 0 warning, 0 suggestion).
