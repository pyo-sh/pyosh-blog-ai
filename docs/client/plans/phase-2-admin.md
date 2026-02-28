# Phase 2: Admin 기본 — Implementation Plan

**Goal:** 관리자 인증, 대시보드, 글 관리, 글 에디터 구현

**Area:** client

**Architecture:** Admin 페이지는 TanStack Query 기반 클라이언트 데이터 페칭. 세션 쿠키 인증 + Next.js middleware로 `/dashboard/*` 보호. CSRF 토큰 처리 추가 필요. Admin 전용 레이아웃(사이드바) 적용.

**Tech Stack:** Next.js 14 (App Router), TanStack Query, TailwindCSS v4

**References:**
- Design doc: `docs/plans/2026-02-28-feature-spec-revision-design.md`
- Feature spec: `docs/client/feature_spec.md` (sections 4.1-4.4, 5.1, 5.4)

**Prerequisites:**
- Phase 1 완료 (Post 엔티티, 글로벌 로딩/에러 등)
- 서버 API 준비 완료: `POST /api/auth/admin/login`, `GET /api/auth/me`, `GET /api/auth/csrf-token`, `GET /api/admin/stats/dashboard`, `GET /api/admin/posts`, `POST /api/admin/posts`, `PATCH /api/admin/posts/:id`

---

## Prerequisite: CSRF 토큰 유틸리티

> 서버는 POST/PUT/DELETE 요청에 CSRF 토큰을 요구함 (`x-csrf-token` 헤더). Phase 2에서 mutation이 처음 발생하므로 여기서 구현.

**Files:**
- Create: `src/shared/api/csrf.ts`
- Modify: `src/shared/api/index.ts`

**Step 1: Create CSRF utility**

```typescript
// src/shared/api/csrf.ts
import { clientFetch } from "./client";

let csrfToken: string | null = null;

export async function getCsrfToken(): Promise<string> {
  if (csrfToken) return csrfToken;

  const data = await clientFetch<{ token: string }>("/api/auth/csrf-token");
  csrfToken = data.token;
  return csrfToken;
}

export function clearCsrfToken(): void {
  csrfToken = null;
}
```

**Step 2: Create mutation helper**

```typescript
// src/shared/api/mutation.ts
import { clientFetch } from "./client";
import { getCsrfToken } from "./csrf";

export async function clientMutate<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = await getCsrfToken();

  return clientFetch<T>(path, {
    ...options,
    headers: {
      ...options.headers,
      "x-csrf-token": token,
    },
  });
}
```

**Step 3: Update exports**

```typescript
// src/shared/api/index.ts — 아래 export 추가
export { getCsrfToken, clearCsrfToken } from "./csrf";
export { clientMutate } from "./mutation";
```

**Step 4: Verify build**

Run: `pnpm compile:types && pnpm lint && pnpm build`
Expected: No errors

**Step 5: Commit**

```bash
git add src/shared/api/
git commit -m "feat: add CSRF token utility and mutation helper"
```

---

## Issue #9: 관리자 인증 + Admin 레이아웃

> **GitHub:** `pyo-sh/pyosh-blog-fe#9`
> **Spec:** feature_spec.md §4.1, §5.4
> **Server API:** `POST /api/auth/admin/login`, `POST /api/auth/admin/logout`, `GET /api/auth/me`

### Task 1: Auth 엔티티

**Files:**
- Create: `src/entities/auth/model.ts`
- Create: `src/entities/auth/api.ts`
- Create: `src/entities/auth/index.ts`

**Step 1: Create Auth types**

```typescript
// src/entities/auth/model.ts
export interface AdminUser {
  type: "admin";
  id: number;
  email: string;
  displayName: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}
```

**Step 2: Create Auth API**

```typescript
// src/entities/auth/api.ts
import { clientFetch, clientMutate } from "@/shared/api";
import type { AdminUser, LoginCredentials } from "./model";

export async function login(credentials: LoginCredentials): Promise<AdminUser> {
  const data = await clientMutate<{ admin: AdminUser }>("/api/auth/admin/login", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
  return data.admin;
}

export async function logout(): Promise<void> {
  await clientMutate<void>("/api/auth/admin/logout", {
    method: "POST",
  });
}

export async function fetchMe(): Promise<AdminUser> {
  return clientFetch<AdminUser>("/api/auth/me");
}

export async function fetchMeServer(
  cookieHeader: string,
): Promise<AdminUser | null> {
  try {
    const { serverFetch } = await import("@/shared/api");
    return await serverFetch<AdminUser>("/api/auth/me", {}, cookieHeader);
  } catch {
    return null;
  }
}
```

**Step 3: Create index**

```typescript
// src/entities/auth/index.ts
export type { AdminUser, LoginCredentials } from "./model";
export { login, logout, fetchMe, fetchMeServer } from "./api";
```

**Step 4: Commit**

```bash
git add src/entities/auth/
git commit -m "feat: add Auth entity types and API"
```

### Task 2: Next.js Middleware (인증 보호)

**Files:**
- Create: `src/middleware.ts`

**Step 1: Create middleware**

```typescript
// src/middleware.ts
import { NextResponse, type NextRequest } from "next/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:5500";

export async function middleware(request: NextRequest) {
  // /dashboard/login은 보호 대상이 아님
  if (request.nextUrl.pathname === "/dashboard/login") {
    return NextResponse.next();
  }

  const cookieHeader = request.headers.get("cookie") ?? "";

  try {
    const response = await fetch(`${API_URL}/api/auth/me`, {
      headers: { Cookie: cookieHeader },
    });

    if (!response.ok) {
      return NextResponse.redirect(new URL("/dashboard/login", request.url));
    }
  } catch {
    return NextResponse.redirect(new URL("/dashboard/login", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: "/dashboard/:path*",
};
```

**Step 2: Verify build**

Run: `pnpm compile:types && pnpm lint && pnpm build`
Expected: No errors

**Step 3: Commit**

```bash
git add src/middleware.ts
git commit -m "feat: add auth middleware for /dashboard/* routes"
```

### Task 3: Admin 레이아웃 (사이드바)

**Files:**
- Create: `src/widgets/admin-sidebar/ui/admin-sidebar.tsx`
- Create: `src/widgets/admin-sidebar/index.ts`
- Create: `src/app/dashboard/layout.tsx`

**Step 1: Create AdminSidebar**

```tsx
// src/widgets/admin-sidebar/ui/admin-sidebar.tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/shared/lib/style-utils";

const navItems = [
  { href: "/dashboard", label: "대시보드", exact: true },
  { href: "/dashboard/posts", label: "글 관리" },
  { href: "/dashboard/categories", label: "카테고리" },
  { href: "/dashboard/comments", label: "댓글" },
  { href: "/dashboard/guestbook", label: "방명록" },
  { href: "/dashboard/assets", label: "에셋" },
];

export function AdminSidebar() {
  const pathname = usePathname();

  const isActive = (href: string, exact?: boolean) =>
    exact ? pathname === href : pathname.startsWith(href);

  return (
    <aside className="w-56 shrink-0 border-r border-border-3 bg-background-1">
      <div className="p-4">
        <Link href="/dashboard" className="text-lg font-bold text-text-1">
          Admin
        </Link>
      </div>
      <nav className="flex flex-col gap-1 px-2">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "rounded px-3 py-2 text-sm",
              isActive(item.href, item.exact)
                ? "bg-primary-1 text-white"
                : "text-text-2 hover:bg-background-2",
            )}
          >
            {item.label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
```

**Step 2: Create index**

```typescript
// src/widgets/admin-sidebar/index.ts
export { AdminSidebar } from "./ui/admin-sidebar";
```

**Step 3: Create Admin layout**

```tsx
// src/app/dashboard/layout.tsx
import { AdminSidebar } from "@/widgets/admin-sidebar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen">
      <AdminSidebar />
      <main className="flex-1 p-6">{children}</main>
    </div>
  );
}
```

> **Note:** Admin 레이아웃에서는 공개 헤더/푸터를 숨김. `app-layer/provider/index.tsx`의 `<Providers>` 래퍼에서 dashboard 경로를 판별하여 Header/Footer 조건부 렌더링 필요.

**Step 4: Verify build**

Run: `pnpm compile:types && pnpm lint && pnpm build`
Expected: No errors

**Step 5: Commit**

```bash
git add src/widgets/admin-sidebar/ src/app/dashboard/layout.tsx
git commit -m "feat: add Admin layout with sidebar navigation"
```

### Task 4: 로그인 페이지

**Files:**
- Create: `src/features/admin-login/ui/login-form.tsx`
- Create: `src/features/admin-login/index.ts`
- Create: `src/app/dashboard/login/page.tsx`
- Create: `src/app/dashboard/login/layout.tsx`

**Step 1: Create LoginForm**

```tsx
// src/features/admin-login/ui/login-form.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/entities/auth";

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await login({ email, password });
      router.push("/dashboard");
      router.refresh();
    } catch {
      setError("이메일 또는 비밀번호가 올바르지 않습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4">
      <div>
        <label htmlFor="email" className="block text-sm font-medium text-text-2">
          이메일
        </label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="mt-1 w-full rounded border border-border-3 bg-background-1 px-3 py-2 text-text-1"
        />
      </div>
      <div>
        <label htmlFor="password" className="block text-sm font-medium text-text-2">
          비밀번호
        </label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className="mt-1 w-full rounded border border-border-3 bg-background-1 px-3 py-2 text-text-1"
        />
      </div>
      {error && <p className="text-sm text-negative-1">{error}</p>}
      <button
        type="submit"
        disabled={loading}
        className="w-full rounded bg-primary-1 py-2 text-white hover:opacity-90 disabled:opacity-50"
      >
        {loading ? "로그인 중..." : "로그인"}
      </button>
    </form>
  );
}
```

**Step 2: Create login page**

```tsx
// src/app/dashboard/login/page.tsx
import { LoginForm } from "@/features/admin-login";

export default function LoginPage() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <div className="w-full max-w-sm">
        <h1 className="mb-8 text-center text-2xl font-bold text-text-1">관리자 로그인</h1>
        <LoginForm />
      </div>
    </div>
  );
}
```

**Step 3: Create login layout (사이드바 없이)**

```tsx
// src/app/dashboard/login/layout.tsx
export default function LoginLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
```

> **Note:** Login 페이지는 Admin 사이드바를 보여주지 않아야 함. dashboard/layout.tsx에서 login 경로를 분기하거나, login/layout.tsx에서 별도 레이아웃 적용.

**Step 4: Create feature index**

```typescript
// src/features/admin-login/index.ts
export { LoginForm } from "./ui/login-form";
```

**Step 5: Verify build**

Run: `pnpm compile:types && pnpm lint && pnpm build`
Expected: No errors

**Step 6: Commit**

```bash
git add src/features/admin-login/ src/app/dashboard/login/
git commit -m "feat: implement admin login page"
```

---

## Issue #10: Admin 대시보드

> **GitHub:** `pyo-sh/pyosh-blog-fe#10`
> **Spec:** feature_spec.md §4.2
> **Server API:** `GET /api/admin/stats/dashboard` → `{ todayPageviews, weekPageviews, monthPageviews, totalPosts, totalComments }`
> **의존:** Issue #9 (Admin 레이아웃 + 인증)

### Task 1: Stat 엔티티

**Files:**
- Create: `src/entities/stat/model.ts`
- Create: `src/entities/stat/api.ts`
- Create: `src/entities/stat/index.ts`

**Step 1: Create Stat types**

```typescript
// src/entities/stat/model.ts
export interface DashboardStats {
  todayPageviews: number;
  weekPageviews: number;
  monthPageviews: number;
  totalPosts: number;
  totalComments: number;
}
```

**Step 2: Create Stat API (TanStack Query)**

```typescript
// src/entities/stat/api.ts
import { clientFetch } from "@/shared/api";
import type { DashboardStats } from "./model";

export async function fetchDashboardStats(): Promise<DashboardStats> {
  return clientFetch<DashboardStats>("/api/admin/stats/dashboard");
}
```

**Step 3: Create index**

```typescript
// src/entities/stat/index.ts
export type { DashboardStats } from "./model";
export { fetchDashboardStats } from "./api";
```

**Step 4: Commit**

```bash
git add src/entities/stat/
git commit -m "feat: add Stat entity for dashboard"
```

### Task 2: 대시보드 페이지

**Files:**
- Create: `src/app/dashboard/page.tsx`

**Step 1: Create dashboard page**

```tsx
// src/app/dashboard/page.tsx
"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchDashboardStats } from "@/entities/stat";

export default function DashboardPage() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ["admin", "dashboard-stats"],
    queryFn: fetchDashboardStats,
  });

  if (isLoading || !stats) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold text-text-1">대시보드</h1>
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="animate-pulse rounded border border-border-3 p-6">
              <div className="h-4 w-20 rounded bg-background-3" />
              <div className="mt-2 h-8 w-16 rounded bg-background-3" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  const cards = [
    { label: "오늘 조회수", value: stats.todayPageviews },
    { label: "주간 조회수", value: stats.weekPageviews },
    { label: "월간 조회수", value: stats.monthPageviews },
    { label: "총 게시글", value: stats.totalPosts },
    { label: "총 댓글", value: stats.totalComments },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold text-text-1">대시보드</h1>
      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {cards.map((card) => (
          <div
            key={card.label}
            className="rounded border border-border-3 p-6"
          >
            <p className="text-sm text-text-3">{card.label}</p>
            <p className="mt-1 text-2xl font-bold text-text-1">
              {card.value.toLocaleString()}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

**Step 2: Verify build**

Run: `pnpm compile:types && pnpm lint && pnpm build`
Expected: No errors

**Step 3: Commit**

```bash
git add src/app/dashboard/page.tsx
git commit -m "feat: implement admin dashboard page"
```

---

## Issue #11: Admin 글 목록 관리

> **GitHub:** `pyo-sh/pyosh-blog-fe#11`
> **Spec:** feature_spec.md §4.3
> **Server API:** `GET /api/admin/posts?page=N&status=...&visibility=...&includeDeleted=...`
> **의존:** Issue #9 (Admin 레이아웃), Issue #7 (Post 엔티티)

### Task 1: Admin Post API 함수

**Files:**
- Modify: `src/entities/post/api.ts`
- Modify: `src/entities/post/index.ts`

**Step 1: Add admin API functions**

`src/entities/post/api.ts`에 추가:

```typescript
import { clientFetch, clientMutate } from "@/shared/api";

interface AdminPostListParams {
  page?: number;
  limit?: number;
  status?: "draft" | "published" | "archived";
  visibility?: "public" | "private";
  categoryId?: number;
  includeDeleted?: boolean;
  q?: string;
}

export async function fetchAdminPosts(
  params: AdminPostListParams = {},
): Promise<PaginatedResponse<Post>> {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set("page", String(params.page));
  if (params.limit) searchParams.set("limit", String(params.limit));
  if (params.status) searchParams.set("status", params.status);
  if (params.visibility) searchParams.set("visibility", params.visibility);
  if (params.categoryId) searchParams.set("categoryId", String(params.categoryId));
  if (params.includeDeleted) searchParams.set("includeDeleted", "true");
  if (params.q) searchParams.set("q", params.q);

  const query = searchParams.toString();
  return clientFetch<PaginatedResponse<Post>>(`/api/admin/posts${query ? `?${query}` : ""}`);
}

export async function deletePost(id: number): Promise<void> {
  await clientMutate<void>(`/api/admin/posts/${id}`, { method: "DELETE" });
}

export async function restorePost(id: number): Promise<Post> {
  const data = await clientMutate<{ post: Post }>(`/api/admin/posts/${id}/restore`, {
    method: "PUT",
  });
  return data.post;
}

export async function hardDeletePost(id: number): Promise<void> {
  await clientMutate<void>(`/api/admin/posts/${id}/hard`, { method: "DELETE" });
}
```

**Step 2: Update exports**

```typescript
// src/entities/post/index.ts — 추가
export { fetchAdminPosts, deletePost, restorePost, hardDeletePost } from "./api";
```

**Step 3: Commit**

```bash
git add src/entities/post/
git commit -m "feat: add admin Post API functions"
```

### Task 2: Admin 글 목록 페이지

**Files:**
- Create: `src/app/dashboard/posts/page.tsx`

**Step 1: Create admin posts page**

```tsx
// src/app/dashboard/posts/page.tsx
"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchAdminPosts, deletePost, restorePost } from "@/entities/post";

export default function AdminPostsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<string>("");
  const [includeDeleted, setIncludeDeleted] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["admin", "posts", { page, status, includeDeleted }],
    queryFn: () =>
      fetchAdminPosts({
        page,
        status: status as "draft" | "published" | "archived" | undefined || undefined,
        includeDeleted,
      }),
  });

  const deleteMutation = useMutation({
    mutationFn: deletePost,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "posts"] }),
  });

  const restoreMutation = useMutation({
    mutationFn: restorePost,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "posts"] }),
  });

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-text-1">글 관리</h1>
        <Link
          href="/dashboard/posts/new"
          className="rounded bg-primary-1 px-4 py-2 text-sm text-white hover:opacity-90"
        >
          새 글 작성
        </Link>
      </div>

      {/* Filters */}
      <div className="mt-4 flex gap-3">
        <select
          value={status}
          onChange={(e) => { setStatus(e.target.value); setPage(1); }}
          className="rounded border border-border-3 bg-background-1 px-3 py-1.5 text-sm text-text-1"
        >
          <option value="">전체 상태</option>
          <option value="draft">초안</option>
          <option value="published">발행됨</option>
          <option value="archived">보관됨</option>
        </select>
        <label className="flex items-center gap-2 text-sm text-text-2">
          <input
            type="checkbox"
            checked={includeDeleted}
            onChange={(e) => { setIncludeDeleted(e.target.checked); setPage(1); }}
          />
          삭제된 글 포함
        </label>
      </div>

      {/* Table */}
      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border-3 text-text-3">
            <tr>
              <th className="py-3">제목</th>
              <th className="py-3">상태</th>
              <th className="py-3">가시성</th>
              <th className="py-3">작성일</th>
              <th className="py-3">작업</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-text-3">
                  로딩 중...
                </td>
              </tr>
            ) : data?.data.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-text-3">
                  게시글이 없습니다.
                </td>
              </tr>
            ) : (
              data?.data.map((post) => (
                <tr key={post.id} className="border-b border-border-3">
                  <td className="py-3">
                    <Link
                      href={`/dashboard/posts/${post.id}/edit`}
                      className="text-text-1 hover:text-primary-1"
                    >
                      {post.title}
                    </Link>
                  </td>
                  <td className="py-3 text-text-3">{post.status}</td>
                  <td className="py-3 text-text-3">{post.visibility}</td>
                  <td className="py-3 text-text-3">
                    {new Date(post.createdAt).toLocaleDateString("ko-KR")}
                  </td>
                  <td className="py-3">
                    {post.deletedAt ? (
                      <button
                        onClick={() => restoreMutation.mutate(post.id)}
                        className="text-sm text-positive-1 hover:underline"
                      >
                        복원
                      </button>
                    ) : (
                      <button
                        onClick={() => deleteMutation.mutate(post.id)}
                        className="text-sm text-negative-1 hover:underline"
                      >
                        삭제
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {data && data.meta.totalPages > 1 && (
        <div className="mt-4 flex justify-center gap-2">
          {Array.from({ length: data.meta.totalPages }, (_, i) => i + 1).map(
            (p) => (
              <button
                key={p}
                onClick={() => setPage(p)}
                className={`rounded px-3 py-1 text-sm ${
                  p === page
                    ? "bg-primary-1 text-white"
                    : "text-text-2 hover:bg-background-2"
                }`}
              >
                {p}
              </button>
            ),
          )}
        </div>
      )}
    </div>
  );
}
```

**Step 2: Verify build**

Run: `pnpm compile:types && pnpm lint && pnpm build`
Expected: No errors

**Step 3: Commit**

```bash
git add src/app/dashboard/posts/page.tsx
git commit -m "feat: implement admin posts list page"
```

---

## Issue #12: 글 에디터 (작성/수정)

> **GitHub:** `pyo-sh/pyosh-blog-fe#12`
> **Spec:** feature_spec.md §4.4
> **Server API:** `POST /api/admin/posts`, `PATCH /api/admin/posts/:id`, `GET /api/admin/posts/:id`, `POST /api/assets/upload`
> **의존:** Issue #9 (Admin 레이아웃), Issue #7 (Post 엔티티)

### Task 1: Post Create/Update API 함수

**Files:**
- Modify: `src/entities/post/api.ts`
- Modify: `src/entities/post/model.ts`

**Step 1: Add types for post creation/update**

`src/entities/post/model.ts`에 추가:

```typescript
export interface CreatePostBody {
  title: string;
  contentMd: string;
  categoryId: number;
  thumbnailUrl?: string | null;
  visibility?: "public" | "private";
  status?: "draft" | "published" | "archived";
  tags?: string[];
  publishedAt?: string;
}

export interface UpdatePostBody {
  title?: string;
  contentMd?: string;
  categoryId?: number;
  thumbnailUrl?: string | null;
  visibility?: "public" | "private";
  status?: "draft" | "published" | "archived";
  tags?: string[];
  publishedAt?: string;
}
```

**Step 2: Add API functions**

`src/entities/post/api.ts`에 추가:

```typescript
export async function fetchAdminPost(id: number): Promise<Post> {
  const data = await clientFetch<{ post: Post }>(`/api/admin/posts/${id}`);
  return data.post;
}

export async function createPost(body: CreatePostBody): Promise<Post> {
  const data = await clientMutate<{ post: Post }>("/api/admin/posts", {
    method: "POST",
    body: JSON.stringify(body),
  });
  return data.post;
}

export async function updatePost(id: number, body: UpdatePostBody): Promise<Post> {
  const data = await clientMutate<{ post: Post }>(`/api/admin/posts/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
  return data.post;
}
```

**Step 3: Update exports**

`src/entities/post/index.ts`에 추가:

```typescript
export type { CreatePostBody, UpdatePostBody } from "./model";
export { fetchAdminPost, createPost, updatePost } from "./api";
```

**Step 4: Commit**

```bash
git add src/entities/post/
git commit -m "feat: add post create/update API functions"
```

### Task 2: 마크다운 에디터 + 프리뷰 Feature

**Files:**
- Create: `src/features/post-editor/ui/markdown-editor.tsx`
- Create: `src/features/post-editor/ui/markdown-preview.tsx`
- Create: `src/features/post-editor/ui/post-form.tsx`
- Create: `src/features/post-editor/index.ts`

**Step 1: Create MarkdownEditor (textarea)**

```tsx
// src/features/post-editor/ui/markdown-editor.tsx
"use client";

interface MarkdownEditorProps {
  value: string;
  onChange: (value: string) => void;
}

export function MarkdownEditor({ value, onChange }: MarkdownEditorProps) {
  return (
    <textarea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder="마크다운으로 작성하세요..."
      className="h-full w-full resize-none border-none bg-background-1 p-4 font-mono text-sm text-text-1 outline-none"
    />
  );
}
```

**Step 2: Create MarkdownPreview**

```tsx
// src/features/post-editor/ui/markdown-preview.tsx
"use client";

import { useState, useEffect } from "react";
import { clientFetch } from "@/shared/api";

interface MarkdownPreviewProps {
  contentMd: string;
}

export function MarkdownPreview({ contentMd }: MarkdownPreviewProps) {
  const [html, setHtml] = useState("");

  useEffect(() => {
    // 클라이언트에서 마크다운 렌더링 (프리뷰용)
    // 방법 1: 서버 API 엔드포인트로 렌더링 위임 (없으면 방법 2)
    // 방법 2: 클라이언트 사이드 렌더링 (간이)
    const render = async () => {
      try {
        const { renderMarkdown } = await import("@/shared/lib/markdown");
        const result = await renderMarkdown(contentMd);
        setHtml(result);
      } catch {
        setHtml(`<p>${contentMd}</p>`);
      }
    };

    const timer = setTimeout(render, 300); // debounce
    return () => clearTimeout(timer);
  }, [contentMd]);

  return (
    <div
      className="prose prose-neutral dark:prose-invert h-full overflow-auto p-4"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
```

> **Note:** shiki는 Node.js 전용일 수 있으므로, 클라이언트 프리뷰에서는 간단한 마크다운 렌더링만 적용하거나 shiki의 브라우저 번들을 사용. 필요시 프리뷰 전용 경량 렌더러 구현.

**Step 3: Create PostForm**

```tsx
// src/features/post-editor/ui/post-form.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { createPost, updatePost, type Post, type CreatePostBody } from "@/entities/post";
import { fetchCategories, type Category } from "@/entities/category";
import { MarkdownEditor } from "./markdown-editor";
import { MarkdownPreview } from "./markdown-preview";

interface PostFormProps {
  post?: Post; // 수정 시 기존 글 데이터
}

export function PostForm({ post }: PostFormProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const isEdit = !!post;

  const [title, setTitle] = useState(post?.title ?? "");
  const [contentMd, setContentMd] = useState(post?.contentMd ?? "");
  const [categoryId, setCategoryId] = useState(post?.categoryId ?? 0);
  const [tags, setTags] = useState(post?.tags.map((t) => t.name).join(", ") ?? "");
  const [status, setStatus] = useState<"draft" | "published" | "archived">(post?.status ?? "draft");
  const [visibility, setVisibility] = useState<"public" | "private">(post?.visibility ?? "public");
  const [thumbnailUrl, setThumbnailUrl] = useState(post?.thumbnailUrl ?? "");

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: () => fetchCategories(),
  });

  // 카테고리 트리를 flat 리스트로 변환
  const flattenCategories = (cats: Category[]): Category[] =>
    cats.flatMap((c) => [c, ...flattenCategories(c.children)]);

  const flatCategories = categories ? flattenCategories(categories) : [];

  const createMutation = useMutation({
    mutationFn: (body: CreatePostBody) => createPost(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "posts"] });
      router.push("/dashboard/posts");
    },
  });

  const updateMutation = useMutation({
    mutationFn: (body: CreatePostBody) => updatePost(post!.id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "posts"] });
      router.push("/dashboard/posts");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const body: CreatePostBody = {
      title,
      contentMd,
      categoryId,
      status,
      visibility,
      thumbnailUrl: thumbnailUrl || null,
      tags: tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean),
    };

    if (isEdit) {
      updateMutation.mutate(body);
    } else {
      createMutation.mutate(body);
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Title */}
      <input
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="제목"
        required
        maxLength={200}
        className="w-full rounded border border-border-3 bg-background-1 px-3 py-2 text-lg font-bold text-text-1"
      />

      {/* Meta fields */}
      <div className="flex flex-wrap gap-3">
        <select
          value={categoryId}
          onChange={(e) => setCategoryId(Number(e.target.value))}
          required
          className="rounded border border-border-3 bg-background-1 px-3 py-1.5 text-sm text-text-1"
        >
          <option value={0} disabled>카테고리 선택</option>
          {flatCategories.map((cat) => (
            <option key={cat.id} value={cat.id}>
              {cat.name}
            </option>
          ))}
        </select>
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value as typeof status)}
          className="rounded border border-border-3 bg-background-1 px-3 py-1.5 text-sm text-text-1"
        >
          <option value="draft">초안</option>
          <option value="published">발행</option>
          <option value="archived">보관</option>
        </select>
        <select
          value={visibility}
          onChange={(e) => setVisibility(e.target.value as typeof visibility)}
          className="rounded border border-border-3 bg-background-1 px-3 py-1.5 text-sm text-text-1"
        >
          <option value="public">공개</option>
          <option value="private">비공개</option>
        </select>
      </div>

      {/* Tags */}
      <input
        type="text"
        value={tags}
        onChange={(e) => setTags(e.target.value)}
        placeholder="태그 (쉼표로 구분)"
        className="w-full rounded border border-border-3 bg-background-1 px-3 py-2 text-sm text-text-1"
      />

      {/* Thumbnail URL */}
      <input
        type="text"
        value={thumbnailUrl}
        onChange={(e) => setThumbnailUrl(e.target.value)}
        placeholder="썸네일 URL"
        className="w-full rounded border border-border-3 bg-background-1 px-3 py-2 text-sm text-text-1"
      />

      {/* Editor + Preview */}
      <div className="grid h-[60vh] grid-cols-2 gap-0 overflow-hidden rounded border border-border-3">
        <div className="border-r border-border-3">
          <MarkdownEditor value={contentMd} onChange={setContentMd} />
        </div>
        <div className="overflow-auto">
          <MarkdownPreview contentMd={contentMd} />
        </div>
      </div>

      {/* Submit */}
      <div className="flex justify-end gap-3">
        <button
          type="button"
          onClick={() => router.back()}
          className="rounded border border-border-3 px-4 py-2 text-sm text-text-2 hover:bg-background-2"
        >
          취소
        </button>
        <button
          type="submit"
          disabled={isPending}
          className="rounded bg-primary-1 px-6 py-2 text-sm text-white hover:opacity-90 disabled:opacity-50"
        >
          {isPending ? "저장 중..." : isEdit ? "수정" : "작성"}
        </button>
      </div>
    </form>
  );
}
```

**Step 4: Create index**

```typescript
// src/features/post-editor/index.ts
export { PostForm } from "./ui/post-form";
```

**Step 5: Verify build**

Run: `pnpm compile:types && pnpm lint && pnpm build`
Expected: No errors

**Step 6: Commit**

```bash
git add src/features/post-editor/
git commit -m "feat: add PostForm with markdown editor and preview"
```

### Task 3: 새 글 작성 / 글 수정 페이지

**Files:**
- Create: `src/app/dashboard/posts/new/page.tsx`
- Create: `src/app/dashboard/posts/[id]/edit/page.tsx`

**Step 1: Create new post page**

```tsx
// src/app/dashboard/posts/new/page.tsx
import { PostForm } from "@/features/post-editor";

export default function NewPostPage() {
  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-text-1">새 글 작성</h1>
      <PostForm />
    </div>
  );
}
```

**Step 2: Create edit post page**

```tsx
// src/app/dashboard/posts/[id]/edit/page.tsx
"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { fetchAdminPost } from "@/entities/post";
import { PostForm } from "@/features/post-editor";

export default function EditPostPage() {
  const params = useParams<{ id: string }>();
  const postId = Number(params.id);

  const { data: post, isLoading } = useQuery({
    queryKey: ["admin", "post", postId],
    queryFn: () => fetchAdminPost(postId),
    enabled: !isNaN(postId),
  });

  if (isLoading) {
    return <div className="text-text-3">로딩 중...</div>;
  }

  if (!post) {
    return <div className="text-text-3">게시글을 찾을 수 없습니다.</div>;
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-text-1">글 수정</h1>
      <PostForm post={post} />
    </div>
  );
}
```

**Step 3: Verify build**

Run: `pnpm compile:types && pnpm lint && pnpm build`
Expected: No errors

**Step 4: Commit**

```bash
git add src/app/dashboard/posts/
git commit -m "feat: implement post new and edit pages"
```

---

## Phase 2 완료 체크리스트

- [ ] CSRF 토큰 유틸리티 + mutation helper
- [ ] Auth 엔티티 (types + API)
- [ ] Next.js middleware (/dashboard/* 보호)
- [ ] Admin 레이아웃 (사이드바)
- [ ] 로그인 페이지
- [ ] Stat 엔티티 + 대시보드 페이지
- [ ] Admin Post API (list, delete, restore)
- [ ] Admin 글 목록 페이지 (필터, 페이지네이션)
- [ ] Post create/update API
- [ ] PostForm (에디터 + 프리뷰)
- [ ] 새 글 작성 / 글 수정 페이지
