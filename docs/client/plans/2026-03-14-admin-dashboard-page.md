# Admin Dashboard Page Implementation Plan

**Goal:** `/dashboard`를 관리자 홈 겸 상세 통계 진입 화면으로 구현한다.
**Area:** client
**Architecture:** App Router의 `src/app/dashboard/page.tsx`에서 화면을 조립하고, 기존 entity/feature 계층의 타입과 API를 재사용한다. 통계는 실데이터 기반 TanStack Query로 연결하고, 최신 댓글은 API 부재 시 샘플 데이터로 분리해 교체 가능한 구조를 유지한다.
**Tech Stack:** Next.js App Router, React, TypeScript, TanStack Query, TailwindCSS

**References:**

- Design doc: `docs/workspace/decisions/2026-03-14-admin-dashboard-design.md`
- Area CLAUDE.md: `client/CLAUDE.md`

---

### Task 1: Existing Dashboard Data Surface Audit

**Files:**

- Inspect: `src/app/dashboard/page.tsx`
- Inspect: `src/entities/stat/**/*`
- Inspect: `src/shared/api/**/*`

**Step 1: Confirm reusable stat query surface**

```tsx
// Identify the current stat entity exports, query hooks, and response shape
// so the dashboard page can consume real data without duplicating fetch logic.
```

**Step 2: Confirm dashboard route and linked admin routes**

```tsx
// Check whether /dashboard already exists and which admin destinations are valid
// for quick actions and recent-comment drill-through links.
```

**Step 3: Verify build**
Run: `pnpm compile:types && pnpm lint && pnpm build`

**Step 4: Commit**
`git add src/app/dashboard src/entities/stat src/shared/api && git commit -m "chore: audit dashboard data surface"`

### Task 2: Build Stats Summary Section

**Files:**

- Modify: `src/app/dashboard/page.tsx`
- Create or Modify: `src/widgets/dashboard/**/*`

**Step 1: Create stats summary UI**

```tsx
"use client";

type DashboardStatCard = {
  label: string;
  value: string;
  description?: string;
};

function DashboardStatsSection({ cards }: { cards: DashboardStatCard[] }) {
  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <a href="/dashboard/stats" className="rounded-md border px-4 py-2 text-sm">
          상세 통계 보기
        </a>
      </div>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5 md:grid-cols-3">
        {cards.map((card) => (
          <article key={card.label} className="rounded-xl border p-4">
            <p className="text-sm text-muted-foreground">{card.label}</p>
            <p className="mt-2 text-2xl font-semibold">{card.value}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
```

**Step 2: Connect TanStack Query stat data**

```tsx
// Map the stat entity response to the five required cards:
// today views, weekly views, monthly views, total posts, total comments.
```

**Step 3: Verify build**
Run: `pnpm compile:types && pnpm lint && pnpm build`

**Step 4: Commit**
`git add src/app/dashboard src/widgets/dashboard && git commit -m "feat: add dashboard stats summary"`

### Task 3: Add Loading and Error States

**Files:**

- Modify: `src/app/dashboard/page.tsx`
- Create or Modify: `src/widgets/dashboard/**/*`

**Step 1: Add card skeletons**

```tsx
function DashboardStatsSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-5 md:grid-cols-3">
      {Array.from({ length: 5 }).map((_, index) => (
        <div key={index} className="h-28 animate-pulse rounded-xl border bg-muted/40" />
      ))}
    </div>
  );
}
```

**Step 2: Add section-level error fallback**

```tsx
// Render a compact error panel for stat load failure while keeping
// the rest of the dashboard available.
```

**Step 3: Verify build**
Run: `pnpm compile:types && pnpm lint && pnpm build`

**Step 4: Commit**
`git add src/app/dashboard src/widgets/dashboard && git commit -m "feat: add dashboard loading states"`

### Task 4: Add Recent Comments Section

**Files:**

- Modify: `src/app/dashboard/page.tsx`
- Create or Modify: `src/widgets/dashboard/**/*`

**Step 1: Define recent comment item shape**

```tsx
type RecentCommentItem = {
  id: string;
  author: string;
  postTitle: string;
  createdAt: string;
  href: string;
};
```

**Step 2: Render read-only recent comments list**

```tsx
function RecentCommentsSection({ items, isSample }: { items: RecentCommentItem[]; isSample: boolean }) {
  return (
    <section className="rounded-xl border p-4">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">최신 댓글</h2>
        {isSample ? <span className="rounded-full border px-2 py-1 text-xs">샘플 데이터</span> : null}
      </div>
      <ul className="space-y-3">
        {items.map((item) => (
          <li key={item.id}>
            <a href={item.href} className="block rounded-lg border p-3">
              <p className="font-medium">{item.author}</p>
              <p className="text-sm text-muted-foreground">{item.postTitle}</p>
              <p className="mt-1 text-xs text-muted-foreground">{item.createdAt}</p>
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}
```

**Step 3: Use real API if available, otherwise inject clearly labeled sample data**

```tsx
// Prefer existing comment/admin APIs. If unavailable, keep data local to the dashboard
// module and label the section as sample data.
```

**Step 4: Verify build**
Run: `pnpm compile:types && pnpm lint && pnpm build`

**Step 5: Commit**
`git add src/app/dashboard src/widgets/dashboard && git commit -m "feat: add dashboard recent comments"`

### Task 5: Add Quick Actions Section and Compose Responsive Layout

**Files:**

- Modify: `src/app/dashboard/page.tsx`
- Create or Modify: `src/widgets/dashboard/**/*`

**Step 1: Define quick action items**

```tsx
type QuickActionItem = {
  label: string;
  description: string;
  href: string;
};
```

**Step 2: Render mixed navigation/action cards**

```tsx
function QuickActionsSection({ items }: { items: QuickActionItem[] }) {
  return (
    <section className="rounded-xl border p-4">
      <h2 className="mb-4 text-lg font-semibold">빠른 이동</h2>
      <div className="grid gap-3 sm:grid-cols-2">
        {items.map((item) => (
          <a key={item.href} href={item.href} className="rounded-lg border p-4">
            <p className="font-medium">{item.label}</p>
            <p className="mt-1 text-sm text-muted-foreground">{item.description}</p>
          </a>
        ))}
      </div>
    </section>
  );
}
```

**Step 3: Compose desktop two-column lower layout**

```tsx
// Stack recent comments and quick actions on mobile.
// Split into two columns on larger screens.
```

**Step 4: Verify build**
Run: `pnpm compile:types && pnpm lint && pnpm build`

**Step 5: Commit**
`git add src/app/dashboard src/widgets/dashboard && git commit -m "feat: add dashboard quick actions"`
