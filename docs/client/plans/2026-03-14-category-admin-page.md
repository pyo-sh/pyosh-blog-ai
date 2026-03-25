# Category Admin Page Implementation Plan

**Goal:** `/dashboard/categories`에서 카테고리 트리 조회와 CRUD 모달을 제공한다.
**Area:** client
**Architecture:** `src/app/dashboard/categories/page.tsx`는 thin entry로 유지하고, 실제 상태 관리와 TanStack Query orchestration은 `src/features/category-manager`에 둔다. 트리 렌더링과 폼 모달은 같은 feature 내부 UI 컴포넌트로 구성해 `app -> features -> entities` 방향을 유지한다.
**Tech Stack:** Next.js App Router, React, TypeScript, TanStack Query, TailwindCSS

**References:**

- Design doc: `docs/workspace/decisions/2026-03-14-category-admin-design.md`
- Area CLAUDE.md: `client/CLAUDE.md`

---

### Task 1: Audit existing category admin contracts

**Files:**

- Inspect: `src/entities/category/api.ts`
- Inspect: `src/entities/category/model.ts`
- Inspect: `src/app/dashboard/**/*`

**Step 1: Confirm admin fetch/mutation surface**

```tsx
// Verify which category admin helpers already exist so the feature can
// reuse them directly instead of adding duplicate transport logic.
```

**Step 2: Confirm dashboard route structure**

```tsx
// Check the current dashboard app routes and layout expectations before
// adding a new categories page entry.
```

**Step 3: Verify build**
Run: `pnpm compile:types && pnpm lint && pnpm build`

**Step 4: Commit**
`git add src/entities/category src/app/dashboard && git commit -m "chore: audit category admin surface"`

### Task 2: Build recursive category tree UI

**Files:**

- Create: `src/features/category-manager/ui/category-tree.tsx`
- Create or Modify: `src/features/category-manager/index.ts`

**Step 1: Create recursive tree row renderer**

```tsx
interface CategoryTreeProps {
  categories: Category[];
  onEdit: (category: Category) => void;
  onDelete: (category: Category) => void;
}
```

**Step 2: Add hidden state and action buttons**

```tsx
// Render name, hidden badge, depth indentation, and edit/delete actions
// for each category row.
```

**Step 3: Verify build**
Run: `pnpm compile:types && pnpm lint && pnpm build`

**Step 4: Commit**
`git add src/features/category-manager && git commit -m "feat: add category tree UI"`

### Task 3: Build shared category form modal

**Files:**

- Create: `src/features/category-manager/ui/category-form-modal.tsx`

**Step 1: Add add/edit mode form component**

```tsx
interface CategoryFormModalProps {
  open: boolean;
  mode: "create" | "edit";
}
```

**Step 2: Add parent selection and hidden toggle**

```tsx
// Support category name input, parent select options, and visibility checkbox.
// Exclude self and descendants from parent candidates in edit mode.
```

**Step 3: Verify build**
Run: `pnpm compile:types && pnpm lint && pnpm build`

**Step 4: Commit**
`git add src/features/category-manager && git commit -m "feat: add category form modal"`

### Task 4: Compose feature root with queries and mutations

**Files:**

- Create or Modify: `src/features/category-manager/index.ts`
- Create: `src/features/category-manager/ui/category-manager.tsx`

**Step 1: Connect TanStack Query list fetch**

```tsx
// Use fetchCategoriesAdmin() through a query and pass normalized tree data
// to CategoryTree.
```

**Step 2: Wire create/update/delete mutations**

```tsx
// Invalidate category queries on success and block delete when children exist.
```

**Step 3: Add empty/loading/error states**

```tsx
// Keep the page usable by showing compact states around the tree region.
```

**Step 4: Verify build**
Run: `pnpm compile:types && pnpm lint && pnpm build`

**Step 5: Commit**
`git add src/features/category-manager && git commit -m "feat: add category manager feature"`

### Task 5: Add dashboard categories page entry

**Files:**

- Create: `src/app/dashboard/categories/page.tsx`

**Step 1: Keep route layer thin**

```tsx
import { CategoryManager } from "@features/category-manager";
```

**Step 2: Render admin page shell**

```tsx
// Add route title/description only if needed, and delegate management UI
// to the feature root component.
```

**Step 3: Verify build**
Run: `pnpm compile:types && pnpm lint && pnpm build`

**Step 4: Commit**
`git add src/app/dashboard/categories src/features/category-manager && git commit -m "feat: add dashboard categories page"`
