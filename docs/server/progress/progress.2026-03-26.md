# Server Progress - 2026-03-26

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
