# Server Progress - 2026-03-26

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
