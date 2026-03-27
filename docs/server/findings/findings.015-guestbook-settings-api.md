# Findings 015 - Guestbook + settings API (Issue #35)

**Date**: 2026-03-26
**Tags**: #guestbook #settings #drizzle #http-semantics #soft-delete

## Context

Implemented the full guestbook public/admin API (8 endpoints) and the site settings API (2 endpoints) as part of issue #35.

## HTTP semantics for reversible vs. irreversible admin actions

Admin operations on guestbook entries were split across two HTTP methods based on reversibility:

- `DELETE` - irreversible destructive actions only: `soft_delete` and `hard_delete`
- `PATCH` - reversible state transitions only: `hide` (active → hidden) and `restore` (hidden → active)

This separation applies to both single-entry routes (`/admin/guestbook/:id`) and bulk routes (`/admin/guestbook/bulk`). The split was arrived at iteratively through code review - the initial implementation mixed all four actions into DELETE.

## Status-guard filtering prevents cross-state contamination

Each state transition applies a source-status filter in the WHERE clause:

- `hide` only updates rows where `status = 'active'` - prevents overwriting `status = 'deleted'` with `hidden`
- `restore` only updates rows where `status = 'hidden'` - prevents `restore` from acting as an `undelete` for soft-deleted entries
- `soft_delete` (bulk) only updates rows where `status != 'deleted'` - preserves original `deletedAt` for idempotent calls
- `soft_delete` (single) returns early if `entry.status === 'deleted'` - same audit-trail preservation

The `adminPatchEntry` single-entry path also needs the status filter even though the entry is fetched first - the fetch and the update are not atomic, and the conceptual contract is clearer with the filter in the UPDATE.

## Drizzle upsert pattern for singleton settings row

The settings table (`site_settings_tb`) always has exactly one row with `id = 1`. `setGuestbookEnabled` uses Drizzle's `onDuplicateKeyUpdate` to implement an upsert without a prior SELECT:

```ts
await this.db
  .insert(siteSettingsTable)
  .values({ id: 1, guestbookEnabled: enabled })
  .onDuplicateKeyUpdate({ set: { guestbookEnabled: enabled } });
```

Pass the typed value directly to `set` - using `sql\`VALUES(guestbook_enabled)\`` is deprecated in Drizzle 0.45 and generates a warning.

## LIKE metacharacter escaping for admin search

The `q` search parameter in `getAdminGuestbook` uses MySQL LIKE against `guestName` and `body`. User input is escaped before interpolation:

```ts
const escaped = query.q.replace(/[%_\\]/g, "\\$&");
const pattern = `%${escaped}%`;
```

The regex `/[%_\\]/g` covers all three MySQL LIKE metacharacters (`%`, `_`, `\`).

## Guestbook enabled check via settings service

`POST /api/guestbook` calls `settingsService.getGuestbookEnabled()` on every request and throws `HttpError.forbidden()` if disabled. The settings fetch is a single-row SELECT with `.limit(1)` and no joins - the overhead is minimal for a blog. A TTL cache was suggested in review but not applied (premature optimization for this use case).

## Review cycle

6 rounds over 5 allowed iterations:

| Round | Critical | Warning | Suggestion | Key issue |
|-------|----------|---------|------------|-----------|
| 1 | 0 | 2 | 1 | DELETE bulk included `restore`; moved to PATCH |
| 2 | 0 | 2 | 0 | DELETE bulk still included `hide`; moved to PATCH |
| 3 | 1 | 1 | 1 | `restore` could undo soft_delete; narrowed to `status='hidden'` filter |
| 4 | 0 | 2 | 0 | Single DELETE included `hide`; separate PATCH /:id added |
| 5 | 0 | 1 | 2 | `hide` could overwrite `status='deleted'`; added active-only guard |
| 6 | 0 | 2 | 2 | soft_delete overwrites `deletedAt` on re-apply; added idempotency guards |

Round 6 warnings were fixed and merged without re-review (round limit reached).
