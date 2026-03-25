# Popular Page Filter Implementation Plan

**Goal:** Add SSR query-based period filtering to `/popular` with canonical redirect behavior and tab UI.
**Area:** client
**Architecture:** The route validates `days` and performs SSR data loading. Presentation is split into a page-local UI component so route logic and rendering stay separate without introducing unnecessary cross-feature abstractions.
**Tech Stack:** Next.js App Router, React Server Components, TypeScript, TailwindCSS v4

**References:**

- Design doc: `docs/workspace/decisions/2026-03-14-popular-page-filter-design.md`
- Area CLAUDE.md: `client/CLAUDE.md`

---

### Task 1: Canonicalize query handling in the popular route

**Files:**

- Modify: `src/app/popular/page.tsx`

**Step 1: Parse and validate `searchParams.days`**

Add route-level logic that accepts only `7` and `30`.

**Step 2: Redirect invalid or missing values**

Use Next.js server redirect to `/popular?days=7`.

**Step 3: Fetch SSR data using the selected period**

Replace the hardcoded default period with the validated `days` value.

**Step 4: Verify build**
Run: `pnpm compile:types && pnpm lint && pnpm build`

### Task 2: Split the page presentation into a local UI component

**Files:**

- Create: `src/app/popular/popular-page-content.tsx`
- Modify: `src/app/popular/page.tsx`

**Step 1: Create a presentation component**

Move hero text, period tabs, list UI, and empty state into a page-local component with typed props.

**Step 2: Render tab links**

Expose `7일 / 30일` links and highlight the active period.

**Step 3: Integrate the component from the route**

Keep `page.tsx` focused on validation, redirect, and fetching.

**Step 4: Verify build**
Run: `pnpm compile:types && pnpm lint && pnpm build`

### Task 3: Final verification and issue completion

**Files:**

- Modify: GitHub issue #61 Definition of Done checkboxes

**Step 1: Run full verification**
Run: `pnpm compile:types && pnpm lint && pnpm build`

**Step 2: Mark completed DoD items**

Check only the items fully implemented by this change.

**Step 3: Commit**
`git add src/app/popular/ && git commit -m "feat: add popular page filter"`
