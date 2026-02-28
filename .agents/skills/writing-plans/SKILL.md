---
name: writing-plans
description: >
  Write detailed implementation plans from specs or requirements before touching code.
  Use when: (1) brainstorming skill produces a design doc, (2) user has a spec and needs
  a step-by-step plan, (3) user says "/writing-plans", "create plan", "implementation plan".
---

# Writing Plans

Write implementation plans with exact file paths, complete code, and test commands. Each task is one 2-5 minute action. DRY. YAGNI. TDD (server). Frequent commits.

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

**Context:** Run in the same worktree where the design doc was created (by brainstorming skill).

**Save to:** `docs/{area}/plans/YYYY-MM-DD-<feature-name>.md`

## Verify Commands

| Area | Test | Build |
|------|------|-------|
| `client` | N/A | `pnpm compile:types && pnpm lint && pnpm build` |
| `server` | `pnpm test` | `pnpm dev` |

## Plan Document Header

```markdown
# [Feature Name] Implementation Plan

**Goal:** [One sentence]
**Area:** [client | server | workspace]
**Architecture:** [2-3 sentences]
**Tech Stack:** [Key technologies]

**References:**
- Design doc: `docs/workspace/decisions/YYYY-MM-DD-<topic>-design.md`
- Area CLAUDE.md: `{area}/CLAUDE.md`

---
```

## Task Structure

### Server (Vitest TDD)

````markdown
### Task N: [Component Name]

**Files:**
- Create: `src/exact/path/to/file.ts`
- Modify: `src/exact/path/to/existing.ts:123-145`
- Test: `src/exact/path/to/__tests__/file.test.ts`

**Step 1: Write failing test**

```typescript
import { describe, it, expect } from 'vitest';

describe('specificBehavior', () => {
  it('should do expected thing', () => {
    const result = functionUnderTest(input);
    expect(result).toEqual(expected);
  });
});
```

**Step 2: Verify failure**
Run: `pnpm test -- src/exact/path/to/__tests__/file.test.ts`

**Step 3: Implement**

```typescript
export function functionUnderTest(input: InputType): OutputType {
  return expected;
}
```

**Step 4: Verify pass**
Run: `pnpm test -- src/exact/path/to/__tests__/file.test.ts`

**Step 5: Commit**
`git add src/exact/path/ && git commit -m "feat: add specific feature"`
````

### Client (Build-Verify)

````markdown
### Task N: [Component Name]

**Files:**
- Create: `src/features/example/ui/example-component.tsx`
- Modify: `src/app/example/page.tsx`

**Step 1: Create component**

```tsx
'use client';

import { cn } from '@/shared/lib/utils';

interface ExampleProps { title: string; }

export function Example({ title }: ExampleProps) {
  return <div className={cn('text-foreground-1')}>{title}</div>;
}
```

**Step 2: Integrate in page**

```tsx
import { Example } from '@/features/example/ui/example-component';
```

**Step 3: Verify build**
Run: `pnpm compile:types && pnpm lint && pnpm build`

**Step 4: Commit**
`git add src/features/example/ src/app/example/ && git commit -m "feat: add example component"`
````

## Rules

- Exact file paths (kebab-case), complete code, exact commands
- Server: TDD with Vitest / Client: build-verify
- Client FSD import direction: `app → widgets → features → entities → shared`
- Commit messages: `{type}: {description}`

## Next Step

After saving the plan, offer choice:

**1. `/dev-issue` now** — Invoke `/dev-issue` to convert the plan directly into GitHub Issues

**2. Split to decisions** — Break the plan into task-sized decision files in `docs/{area}/decisions/`, each following the repo's `.github/ISSUE_TEMPLATE` field structure, for later `/dev-issue` conversion
