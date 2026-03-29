---
id: "016"
title: "Categories API (Issue #34)"
date: 2026-03-26
tags: ["#categories", "#drizzle", "#toctou", "#tree", "#migration"]
---

# Findings 016 - Categories API (Issue #34)

## Context

Implemented the full Categories API: `GET /api/categories` (tree with post counts), `POST /api/categories`, `PATCH /api/categories/tree` (batch), `PATCH /api/categories/:id`, `DELETE /api/categories/:id` (action=move|trash).

## Key findings

### 1. In-memory target-state cycle detection for batch tree updates

When validating a batch parentId change, using the current DB state causes false rejections for valid parent-child position swaps (A→parent of B, B→parent of A).

The correct approach: fetch all categories once, build a `targetMap` that reflects the intended state after applying the full batch, then walk the `targetMap` in-memory to check for cycles. No per-item DB queries needed.

```typescript
// Apply all changes to the map first
for (const item of items) {
  targetMap.set(item.id, item.parentId);
}
// Then walk the map for each item
let current: number | null = item.parentId;
while (current !== null) {
  if (current === item.id) { hasCycle = true; break; }
  current = targetMap.get(current) ?? null;
}
```

### 2. FOR SHARE lock inside transaction closes TOCTOU window

When the `allCategories` fetch and the batch UPDATE run in separate transactions, a concurrent delete between them could allow a stale parentId to pass the existence check and then reference a non-existent category.

Fix: run the fetch inside the transaction with `.for("share")` - prevents concurrent deletes from acquiring an exclusive lock until the transaction commits.

```typescript
const allCategories = await tx
  .select({ id: categoryTable.id, parentId: categoryTable.parentId })
  .from(categoryTable)
  .for("share");
```

### 3. nullable categoryId needed for orphaned posts on category delete

`post_tb.category_id` was `NOT NULL`. When deleting a category with `action=trash`, posts need their `categoryId` set to `null` (not just soft-deleted) so they don't hold orphaned FK references after the category row is deleted. Same applies to already-soft-deleted posts in the `action=move` branch.

Required schema change: `ALTER TABLE post_tb MODIFY COLUMN category_id int` (remove NOT NULL) and a new Drizzle migration (0005).

### 4. Drizzle migration snapshot IDs must be UUIDs

The `drizzle/meta/_journal.json` and snapshot files require proper UUID values (e.g. `"bd618725-39b6-481b-8db8-9a41964925ad"`) in the `id`/`prevId` fields. Using a plain string like `"snapshot_0004"` fails the snapshot chain validation. Generate with Python `str(uuid.uuid4())`.

### 5. sql`NOW()` over new Date() for DB-side timestamps

Using `new Date()` (JavaScript runtime clock) for `deletedAt` risks subtle drift if the app and DB server clocks diverge. All other timestamp columns use DB-side defaults. Use `sql\`NOW()\`` for consistency.

```typescript
// Before
.set({ deletedAt: new Date(), categoryId: null })
// After
.set({ deletedAt: sql`NOW()`, categoryId: null })
```

### 6. Static route `/tree` must be registered before `/:id`

In Fastify, a static path segment (`/tree`) and a dynamic one (`/:id`) at the same prefix will match in registration order. `PATCH /api/categories/tree` must be registered before `PATCH /api/categories/:id` to avoid `"tree"` being captured as an id parameter.

### 7. Cache-Control must be conditional on admin flag

`GET /api/categories` supports an `include_hidden=true` query for admins that returns hidden categories not visible to the public. Setting `Cache-Control: public, max-age=300` unconditionally leaks admin-only data to shared caches.

Fix: return `no-store` when `includeHidden=true`, `public, max-age=300` otherwise.

## Review rounds

11 standard review rounds + 1 suggestion-only round (skipped re-review). Key corrections across rounds:
- Round 1: no cycle detection, child count check outside transaction
- Round 2: cycle detection used DB state (false rejections for swaps)
- Round 3: missing item.id existence check, moveTo guard removed
- Round 4: moveTo===id guard missing, duplicate IDs in changes allowed
- Round 5: action=trash left orphaned categoryId; made categoryId nullable
- Round 6: snapshot UUIDs invalid format
- Round 7: action=move moved already-deleted posts to target
- Round 8: 403 test sent empty changes array (400 before auth check)
- Round 9: TOCTOU note added, NULL categoryId included in post counts GROUP BY
- Round 10: missing DB-level assertions in trash/move tests
- Round 11: unconditional Cache-Control header, missing changes.max(200)
- Round 12: allCategories fetch outside transaction (TOCTOU), missing moveTo-not-found test
