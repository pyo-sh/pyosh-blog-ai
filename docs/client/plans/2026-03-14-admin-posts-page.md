# Admin Posts Page Implementation Plan

**Goal:** `/dashboard/posts` 관리자 글 목록 페이지를 구현한다.
**Area:** client
**Architecture:** App Router의 `src/app/dashboard/posts/page.tsx`를 `use client` 페이지로 구성하고, `entities/post`의 관리자 API를 사용해 페이지 상태 기반 서버 페이징 목록을 조회한다. 필터와 mutation 상태는 페이지 내부에서 관리하고, TanStack Query로 조회 캐시 무효화를 처리한다.
**Tech Stack:** Next.js App Router, React, TypeScript, TanStack Query, TailwindCSS

**References:**

- Design doc: `docs/workspace/decisions/2026-03-14-admin-posts-page-design.md`
- Area CLAUDE.md: `client/CLAUDE.md`

---

### Task 1: Admin Post API Surface Align

**Files:**

- Modify: `src/entities/post/model.ts`
- Modify: `src/entities/post/api.ts`
- Modify: `src/entities/post/index.ts`

**Step 1: Add admin list query types**

```ts
export interface FetchAdminPostsParams {
  page?: number;
  limit?: number;
  status?: "draft" | "published" | "archived";
  includeDeleted?: boolean;
}
```

**Step 2: Add admin list and mutation helpers**

```ts
export async function fetchAdminPosts(params: FetchAdminPostsParams): Promise<PaginatedResponse<Post>> {
  // build admin query string and call clientFetch/serverFetch as needed
}
```

**Step 3: Verify build**
Run: `pnpm compile:types && pnpm lint && pnpm build`

**Step 4: Commit**
`git add src/entities/post && git commit -m "feat: add admin post list api"`

### Task 2: Build Admin Posts Page Shell

**Files:**

- Create: `src/app/dashboard/posts/page.tsx`

**Step 1: Add page header and CTA**

```tsx
<header className="flex items-center justify-between">
  <div>
    <h1 className="text-2xl font-semibold">글 관리</h1>
    <p className="text-sm text-text-3">상태별 글을 조회하고 삭제 또는 복원할 수 있습니다.</p>
  </div>
  <Link href="/dashboard/posts/new">새 글 작성</Link>
</header>
```

**Step 2: Add filter state and query wiring**

```tsx
const [page, setPage] = useState(1);
const [status, setStatus] = useState<AdminPostStatusFilter>("all");
const [includeDeleted, setIncludeDeleted] = useState(false);
```

**Step 3: Verify build**
Run: `pnpm compile:types && pnpm lint && pnpm build`

**Step 4: Commit**
`git add src/app/dashboard/posts/page.tsx && git commit -m "feat: add admin posts page shell"`

### Task 3: Render Table and Empty/Error States

**Files:**

- Modify: `src/app/dashboard/posts/page.tsx`

**Step 1: Render admin posts table**

```tsx
<table>
  <thead>{/* title, status, visibility, createdAt, actions */}</thead>
  <tbody>{/* rows */}</tbody>
</table>
```

**Step 2: Add loading, empty, and error states**

```tsx
if (isLoading) return <div>불러오는 중...</div>;
if (isError) return <button onClick={() => refetch()}>다시 시도</button>;
```

**Step 3: Verify build**
Run: `pnpm compile:types && pnpm lint && pnpm build`

**Step 4: Commit**
`git add src/app/dashboard/posts/page.tsx && git commit -m "feat: add admin posts table states"`

### Task 4: Add Delete and Restore Actions

**Files:**

- Modify: `src/app/dashboard/posts/page.tsx`

**Step 1: Add mutations**

```tsx
const deleteMutation = useMutation({ mutationFn: deletePost });
const restoreMutation = useMutation({ mutationFn: restorePost });
```

**Step 2: Invalidate list query after success**

```tsx
await queryClient.invalidateQueries({ queryKey: ["admin-posts"] });
```

**Step 3: Verify build**
Run: `pnpm compile:types && pnpm lint && pnpm build`

**Step 4: Commit**
`git add src/app/dashboard/posts/page.tsx && git commit -m "feat: add admin post actions"`

### Task 5: Add Pagination Controls and Final Polish

**Files:**

- Modify: `src/app/dashboard/posts/page.tsx`

**Step 1: Render pagination controls**

```tsx
<nav>
  <button onClick={() => setPage((value) => value - 1)}>이전</button>
  <span>{page}</span>
  <button onClick={() => setPage((value) => value + 1)}>다음</button>
</nav>
```

**Step 2: Reset page on filter change and disable invalid actions**

```tsx
setPage(1);
```

**Step 3: Verify build**
Run: `pnpm compile:types && pnpm lint && pnpm build`

**Step 4: Commit**
`git add src/app/dashboard/posts/page.tsx && git commit -m "feat: finish admin posts page"`
