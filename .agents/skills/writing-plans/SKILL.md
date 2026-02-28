---
name: writing-plans
description: Use when you have a spec or requirements for a multi-step task, before touching code
---

# Writing Plans

## Overview

Write comprehensive implementation plans assuming the engineer has zero context for our codebase and questionable taste. Document everything they need to know: which files to touch for each task, code, testing, docs they might need to check, how to test it. Give them the whole plan as bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

Assume they are a skilled developer, but know almost nothing about our toolset or problem domain. Assume they don't know good test design very well.

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

**Context:** This should be run in the same worktree where the design doc was created (by brainstorming skill).

**Save plans to:** `docs/{area}/plans/YYYY-MM-DD-<feature-name>.md`

## Project Context

This is a monorepo with independent Git repos per area. Always specify the target area.

| Area | Tech Stack | Test Command | Build/Verify |
|------|-----------|-------------|--------------|
| `client` | Next.js 14, React 18, TypeScript, TailwindCSS 4 | `pnpm build && pnpm lint && pnpm compile:types` | `pnpm build` |
| `server` | Fastify 5, Drizzle ORM, MySQL, Zod, Vitest | `pnpm test` | `pnpm dev` |
| `workspace` | Skills, docs, config | N/A | N/A |

- Package manager: **pnpm**
- File naming: **kebab-case**
- TypeScript Strict Mode
- ESLint + Prettier auto-formatting

## Bite-Sized Task Granularity

**Each step is one action (2-5 minutes):**
- "Write the failing test" — step
- "Run it to make sure it fails" — step
- "Implement the minimal code to make the test pass" — step
- "Run the tests and make sure they pass" — step
- "Commit" — step

## Plan Document Header

**Every plan MUST start with this header:**

```markdown
# [Feature Name] Implementation Plan

**Goal:** [One sentence describing what this builds]

**Area:** [client | server | workspace]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries from the area]

**References:**
- Design doc: `docs/workspace/decisions/YYYY-MM-DD-<topic>-design.md`
- Area CLAUDE.md: `{area}/CLAUDE.md`

---
```

## Task Structure

### Server Area (Vitest TDD)

````markdown
### Task N: [Component Name]

**Files:**
- Create: `src/exact/path/to/file.ts`
- Modify: `src/exact/path/to/existing.ts:123-145`
- Test: `src/exact/path/to/__tests__/file.test.ts`

**Step 1: Write the failing test**

```typescript
import { describe, it, expect } from 'vitest';

describe('specificBehavior', () => {
  it('should do expected thing', () => {
    const result = functionUnderTest(input);
    expect(result).toEqual(expected);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `pnpm test -- src/exact/path/to/__tests__/file.test.ts`
Expected: FAIL with "functionUnderTest is not defined"

**Step 3: Write minimal implementation**

```typescript
export function functionUnderTest(input: InputType): OutputType {
  return expected;
}
```

**Step 4: Run test to verify it passes**

Run: `pnpm test -- src/exact/path/to/__tests__/file.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add src/exact/path/
git commit -m "feat: add specific feature"
```
````

### Client Area (Build-Verify)

Client has no test framework — verify via build + lint + type check.

````markdown
### Task N: [Component Name]

**Files:**
- Create: `src/features/example/ui/example-component.tsx`
- Modify: `src/app/example/page.tsx`

**Step 1: Create component**

```tsx
'use client';

import { cn } from '@/shared/lib/utils';

interface ExampleProps {
  title: string;
}

export function Example({ title }: ExampleProps) {
  return <div className={cn('text-foreground-1')}>{title}</div>;
}
```

**Step 2: Integrate in page**

```tsx
import { Example } from '@/features/example/ui/example-component';
// ...
```

**Step 3: Verify build**

Run: `pnpm compile:types && pnpm lint && pnpm build`
Expected: No errors

**Step 4: Commit**

```bash
git add src/features/example/ src/app/example/
git commit -m "feat: add example component"
```
````

## Remember

- Exact file paths always (kebab-case)
- Complete code in plan (not "add validation")
- Exact commands with expected output
- Server: TDD with Vitest (`pnpm test`)
- Client: Build-verify (`pnpm compile:types && pnpm lint && pnpm build`)
- Import direction (client FSD): `app → widgets → features → entities → shared`
- Commit messages: `{type}: {description}`
- DRY, YAGNI, TDD (server), frequent commits

## Next Step

After saving the plan, offer choice:

**1. `/dev-issue` now** — Invoke `/dev-issue` to convert the plan directly into GitHub Issues

**2. Split to decisions** — Break the plan into task-sized decision files in `docs/{area}/decisions/`, each following the repo's `.github/ISSUE_TEMPLATE` field structure, for later `/dev-issue` conversion
