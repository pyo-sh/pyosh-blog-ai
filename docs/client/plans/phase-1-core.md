# Phase 1: 핵심 골격 — Implementation Plan

**Goal:** 블로그 핵심 공개 페이지 구현 (홈 글 목록, 글 상세, 카테고리 네비게이션)

**Area:** client

**Architecture:** Server Components(SSR)로 초기 데이터 fetch → 정적 HTML 렌더링. Post/Category 엔티티를 entities/ 계층에 정의하고, features/ 계층에서 UI 조합. FSD import 방향(`app → widgets → features → entities → shared`) 준수.

**Tech Stack:** Next.js 14 (App Router), TailwindCSS v4, unified + remark + rehype + shiki (마크다운), next/image

**References:**
- Design doc: `docs/plans/2026-02-28-feature-spec-revision-design.md`
- Area CLAUDE.md: `client/CLAUDE.md`
- Feature spec: `docs/client/feature_spec.md` (sections 3.1-3.4, 5.1-5.2, 5.5-5.6)

**Prerequisites:**
- API 클라이언트 설정 완료 (Issue #4 ✅)
- 서버 API 준비 완료: `GET /api/posts`, `GET /api/posts/:slug`, `GET /api/categories`, `GET /api/tags`

---

## Prerequisite: PaginatedResponse 타입 수정

> **중요:** 서버는 `meta.total`을 반환하지만 클라이언트 타입은 `meta.totalCount`로 정의됨. Phase 1 시작 전 반드시 수정.

**Files:**
- Modify: `src/shared/api/types.ts`

**Step 1: Fix PaginatedResponse meta field**

```typescript
// src/shared/api/types.ts
export interface PaginatedResponse<T> {
  data: T[];
  meta: {
    page: number;
    limit: number;
    total: number;      // ← totalCount → total (서버 스키마와 일치)
    totalPages: number;
  };
}
```

**Step 2: Verify build**

Run: `pnpm compile:types && pnpm lint && pnpm build`
Expected: No errors

**Step 3: Commit**

```bash
git add src/shared/api/types.ts
git commit -m "fix: align PaginatedResponse meta.total with server schema"
```

---

## Issue #7: 홈 — 글 목록 페이지

> **GitHub:** `pyo-sh/pyosh-blog-fe#7`
> **Spec:** feature_spec.md §3.1
> **Server API:** `GET /api/posts?page=N&limit=10` → `{ data: Post[], meta: PaginationMeta }`

### Task 1: Post 엔티티 타입 정의

**Files:**
- Create: `src/entities/post/model.ts`
- Create: `src/entities/post/index.ts`

**Step 1: Create Post types**

```typescript
// src/entities/post/model.ts

export interface PostTag {
  id: number;
  name: string;
  slug: string;
}

export interface PostCategory {
  id: number;
  name: string;
  slug: string;
}

export interface Post {
  id: number;
  categoryId: number;
  title: string;
  slug: string;
  contentMd: string;
  thumbnailUrl: string | null;
  visibility: "public" | "private";
  status: "draft" | "published" | "archived";
  publishedAt: string | null;
  createdAt: string;
  updatedAt: string;
  deletedAt: string | null;
  category: PostCategory;
  tags: PostTag[];
}

export interface PostNavigation {
  slug: string;
  title: string;
}
```

**Step 2: Create public exports**

```typescript
// src/entities/post/index.ts
export type { Post, PostTag, PostCategory, PostNavigation } from "./model";
```

**Step 3: Commit**

```bash
git add src/entities/post/
git commit -m "feat: add Post entity types"
```

### Task 2: Post API 함수

**Files:**
- Create: `src/entities/post/api.ts`
- Modify: `src/entities/post/index.ts`

**Step 1: Create Post API functions**

```typescript
// src/entities/post/api.ts
import { serverFetch } from "@/shared/api";
import type { PaginatedResponse } from "@/shared/api";
import type { Post, PostNavigation } from "./model";

interface PostListParams {
  page?: number;
  limit?: number;
  categoryId?: number;
  tagSlug?: string;
  q?: string;
}

export async function fetchPosts(
  params: PostListParams = {},
  cookieHeader?: string,
): Promise<PaginatedResponse<Post>> {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set("page", String(params.page));
  if (params.limit) searchParams.set("limit", String(params.limit));
  if (params.categoryId) searchParams.set("categoryId", String(params.categoryId));
  if (params.tagSlug) searchParams.set("tagSlug", params.tagSlug);
  if (params.q) searchParams.set("q", params.q);

  const query = searchParams.toString();
  const path = `/api/posts${query ? `?${query}` : ""}`;

  return serverFetch<PaginatedResponse<Post>>(path, {}, cookieHeader);
}

interface PostDetailResponse {
  post: Post;
  prevPost: PostNavigation | null;
  nextPost: PostNavigation | null;
}

export async function fetchPostBySlug(
  slug: string,
  cookieHeader?: string,
): Promise<PostDetailResponse> {
  return serverFetch<PostDetailResponse>(`/api/posts/${slug}`, {}, cookieHeader);
}
```

**Step 2: Update exports**

```typescript
// src/entities/post/index.ts
export type { Post, PostTag, PostCategory, PostNavigation } from "./model";
export { fetchPosts, fetchPostBySlug } from "./api";
```

**Step 3: Verify build**

Run: `pnpm compile:types && pnpm lint && pnpm build`
Expected: No errors

**Step 4: Commit**

```bash
git add src/entities/post/
git commit -m "feat: add Post entity API functions"
```

### Task 3: Pagination 컴포넌트

**Files:**
- Create: `src/shared/ui/libs/pagination.tsx`
- Modify: `src/shared/ui/libs/index.tsx`

**Step 1: Create Pagination component**

```tsx
// src/shared/ui/libs/pagination.tsx
import Link from "next/link";
import { cn } from "@/shared/lib/style-utils";

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  basePath: string;
  queryParams?: Record<string, string>;
}

export function Pagination({
  currentPage,
  totalPages,
  basePath,
  queryParams = {},
}: PaginationProps) {
  if (totalPages <= 1) return null;

  const getHref = (page: number) => {
    const params = new URLSearchParams(queryParams);
    if (page > 1) params.set("page", String(page));
    const query = params.toString();
    return `${basePath}${query ? `?${query}` : ""}`;
  };

  const pages = Array.from({ length: totalPages }, (_, i) => i + 1);

  return (
    <nav aria-label="Pagination" className="flex items-center justify-center gap-2 py-8">
      {currentPage > 1 && (
        <Link
          href={getHref(currentPage - 1)}
          className="rounded px-3 py-2 text-text-2 hover:bg-background-2"
        >
          이전
        </Link>
      )}
      {pages.map((page) => (
        <Link
          key={page}
          href={getHref(page)}
          className={cn(
            "rounded px-3 py-2",
            page === currentPage
              ? "bg-primary-1 text-white"
              : "text-text-2 hover:bg-background-2",
          )}
        >
          {page}
        </Link>
      ))}
      {currentPage < totalPages && (
        <Link
          href={getHref(currentPage + 1)}
          className="rounded px-3 py-2 text-text-2 hover:bg-background-2"
        >
          다음
        </Link>
      )}
    </nav>
  );
}
```

**Step 2: Add export**

`src/shared/ui/libs/index.tsx`에 `export { Pagination } from "./pagination";` 추가.

**Step 3: Verify build**

Run: `pnpm compile:types && pnpm lint && pnpm build`
Expected: No errors

**Step 4: Commit**

```bash
git add src/shared/ui/libs/pagination.tsx src/shared/ui/libs/index.tsx
git commit -m "feat: add Pagination component"
```

### Task 4: PostCard 컴포넌트

**Files:**
- Create: `src/features/post-list/ui/post-card.tsx`
- Create: `src/features/post-list/index.ts`

**Step 1: Create PostCard**

```tsx
// src/features/post-list/ui/post-card.tsx
import Link from "next/link";
import Image from "next/image";
import { cn } from "@/shared/lib/style-utils";
import type { Post } from "@/entities/post";

interface PostCardProps {
  post: Post;
}

export function PostCard({ post }: PostCardProps) {
  const summary = post.contentMd.slice(0, 200).replace(/[#*`>\-\[\]]/g, "").trim();
  const formattedDate = post.publishedAt
    ? new Date(post.publishedAt).toLocaleDateString("ko-KR")
    : new Date(post.createdAt).toLocaleDateString("ko-KR");

  return (
    <article className="border-b border-border-3 py-6">
      <Link href={`/posts/${post.slug}`} className="group flex gap-6">
        {post.thumbnailUrl && (
          <div className="relative hidden h-32 w-48 shrink-0 overflow-hidden rounded sm:block">
            <Image
              src={post.thumbnailUrl}
              alt={post.title}
              fill
              sizes="192px"
              className="object-cover"
            />
          </div>
        )}
        <div className="flex min-w-0 flex-1 flex-col justify-between">
          <div>
            <h2 className="text-lg font-bold text-text-1 group-hover:text-primary-1">
              {post.title}
            </h2>
            <p className="mt-1 line-clamp-2 text-sm text-text-3">{summary}</p>
          </div>
          <div className="mt-3 flex items-center gap-3 text-xs text-text-4">
            <span>{post.category.name}</span>
            <span>{formattedDate}</span>
            {post.tags.length > 0 && (
              <div className="flex gap-1">
                {post.tags.map((tag) => (
                  <span key={tag.id} className="rounded bg-background-3 px-1.5 py-0.5">
                    {tag.name}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </Link>
    </article>
  );
}
```

**Step 2: Create index**

```typescript
// src/features/post-list/index.ts
export { PostCard } from "./ui/post-card";
```

**Step 3: Verify build**

Run: `pnpm compile:types && pnpm lint && pnpm build`
Expected: No errors

**Step 4: Commit**

```bash
git add src/features/post-list/
git commit -m "feat: add PostCard component"
```

### Task 5: 홈 페이지 구현

**Files:**
- Modify: `src/app/page.tsx`

**Step 1: Implement home page (SSR)**

```tsx
// src/app/page.tsx
import { fetchPosts } from "@/entities/post";
import { PostCard } from "@/features/post-list";
import { Pagination } from "@/shared/ui/libs";

interface HomePageProps {
  searchParams: Promise<{ page?: string }>;
}

export default async function HomePage({ searchParams }: HomePageProps) {
  const params = await searchParams;
  const page = Number(params.page) || 1;
  const { data: posts, meta } = await fetchPosts({ page });

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <section>
        {posts.length === 0 ? (
          <p className="py-16 text-center text-text-3">게시글이 없습니다.</p>
        ) : (
          posts.map((post) => <PostCard key={post.id} post={post} />)
        )}
      </section>
      <Pagination currentPage={page} totalPages={meta.totalPages} basePath="/" />
    </main>
  );
}
```

**Step 2: Verify build**

Run: `pnpm compile:types && pnpm lint && pnpm build`
Expected: No errors

**Step 3: Commit**

```bash
git add src/app/page.tsx
git commit -m "feat: implement home page with post list and pagination"
```

### Task 6: 글로벌 로딩/에러/404 페이지

**Files:**
- Create: `src/app/loading.tsx`
- Create: `src/app/error.tsx`
- Create: `src/app/not-found.tsx`

**Step 1: Create loading page**

```tsx
// src/app/loading.tsx
export default function Loading() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <div className="space-y-6">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="animate-pulse border-b border-border-3 py-6">
            <div className="h-5 w-3/4 rounded bg-background-3" />
            <div className="mt-2 h-4 w-full rounded bg-background-3" />
            <div className="mt-1 h-4 w-2/3 rounded bg-background-3" />
            <div className="mt-3 flex gap-3">
              <div className="h-3 w-16 rounded bg-background-3" />
              <div className="h-3 w-20 rounded bg-background-3" />
            </div>
          </div>
        ))}
      </div>
    </main>
  );
}
```

**Step 2: Create error page**

```tsx
// src/app/error.tsx
"use client";

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ErrorPage({ error, reset }: ErrorPageProps) {
  return (
    <main className="flex min-h-[50vh] flex-col items-center justify-center px-4">
      <h2 className="text-xl font-bold text-text-1">오류가 발생했습니다</h2>
      <p className="mt-2 text-text-3">{error.message}</p>
      <button
        onClick={reset}
        className="mt-6 rounded bg-primary-1 px-4 py-2 text-white hover:opacity-90"
      >
        다시 시도
      </button>
    </main>
  );
}
```

**Step 3: Create not-found page**

```tsx
// src/app/not-found.tsx
import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-[50vh] flex-col items-center justify-center px-4">
      <h2 className="text-xl font-bold text-text-1">404</h2>
      <p className="mt-2 text-text-3">페이지를 찾을 수 없습니다.</p>
      <Link
        href="/"
        className="mt-6 rounded bg-primary-1 px-4 py-2 text-white hover:opacity-90"
      >
        홈으로 돌아가기
      </Link>
    </main>
  );
}
```

**Step 4: Verify build**

Run: `pnpm compile:types && pnpm lint && pnpm build`
Expected: No errors

**Step 5: Commit**

```bash
git add src/app/loading.tsx src/app/error.tsx src/app/not-found.tsx
git commit -m "feat: add global loading, error, and not-found pages"
```

---

## Issue #5: 글 상세 페이지 — 마크다운 렌더링 파이프라인

> **GitHub:** `pyo-sh/pyosh-blog-fe#5`
> **Spec:** feature_spec.md §3.2, §5.2, §5.5
> **Server API:** `GET /api/posts/:slug` → `{ post, prevPost, nextPost }`
> **의존:** Issue #7 (Post 엔티티 필요)

### Task 1: 마크다운 의존성 설치

**Step 1: Install packages**

```bash
cd client
pnpm add unified remark-parse remark-rehype rehype-stringify rehype-sanitize shiki @shikijs/rehype
```

**Step 2: Commit**

```bash
git add package.json pnpm-lock.yaml
git commit -m "feat: add markdown rendering dependencies"
```

### Task 2: 마크다운 렌더링 유틸리티

**Files:**
- Create: `src/shared/lib/markdown.ts`

**Step 1: Create markdown renderer**

```typescript
// src/shared/lib/markdown.ts
import { unified } from "unified";
import remarkParse from "remark-parse";
import remarkRehype from "remark-rehype";
import rehypeStringify from "rehype-stringify";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import rehypeShiki from "@shikijs/rehype";

const sanitizeSchema = {
  ...defaultSchema,
  attributes: {
    ...defaultSchema.attributes,
    code: [...(defaultSchema.attributes?.code ?? []), "className"],
    span: [...(defaultSchema.attributes?.span ?? []), "className", "style"],
    pre: [...(defaultSchema.attributes?.pre ?? []), "className", "style"],
  },
};

export async function renderMarkdown(md: string): Promise<string> {
  const result = await unified()
    .use(remarkParse)
    .use(remarkRehype)
    .use(rehypeShiki, {
      theme: "github-dark",
    })
    .use(rehypeSanitize, sanitizeSchema)
    .use(rehypeStringify)
    .process(md);

  return String(result);
}
```

> **Note:** shiki 테마 선택(`github-dark`)은 dark/light mode에 따라 조정 가능. 초기에는 단일 테마로 시작.
> sanitize schema에서 shiki가 생성하는 `style` attribute를 허용해야 코드 하이라이팅이 동작함.

**Step 2: Verify build**

Run: `pnpm compile:types && pnpm lint && pnpm build`
Expected: No errors

**Step 3: Commit**

```bash
git add src/shared/lib/markdown.ts
git commit -m "feat: add markdown rendering utility with shiki"
```

### Task 3: PostContent 컴포넌트

**Files:**
- Create: `src/features/post-detail/ui/post-content.tsx`
- Create: `src/features/post-detail/index.ts`

**Step 1: Create PostContent (Server Component)**

```tsx
// src/features/post-detail/ui/post-content.tsx
import { renderMarkdown } from "@/shared/lib/markdown";

interface PostContentProps {
  contentMd: string;
}

export async function PostContent({ contentMd }: PostContentProps) {
  const html = await renderMarkdown(contentMd);

  return (
    <div
      className="prose prose-neutral dark:prose-invert max-w-none"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
```

> **Note:** TailwindCSS v4의 `@tailwindcss/typography` 플러그인이 필요할 수 있음. 없으면 마크다운 HTML에 직접 스타일 적용.
> `@tailwindcss/typography`가 없는 경우 `prose` 클래스 대신 커스텀 CSS 클래스를 `app-layer/style/`에 추가.

**Step 2: Create PostNavigation**

```tsx
// src/features/post-detail/ui/post-navigation.tsx
import Link from "next/link";
import type { PostNavigation as PostNav } from "@/entities/post";

interface PostNavigationProps {
  prevPost: PostNav | null;
  nextPost: PostNav | null;
}

export function PostNavigation({ prevPost, nextPost }: PostNavigationProps) {
  if (!prevPost && !nextPost) return null;

  return (
    <nav className="mt-12 flex items-stretch gap-4 border-t border-border-3 pt-8">
      {prevPost ? (
        <Link
          href={`/posts/${prevPost.slug}`}
          className="flex flex-1 flex-col rounded border border-border-3 p-4 hover:bg-background-2"
        >
          <span className="text-xs text-text-4">이전 글</span>
          <span className="mt-1 text-sm font-medium text-text-1">{prevPost.title}</span>
        </Link>
      ) : (
        <div className="flex-1" />
      )}
      {nextPost ? (
        <Link
          href={`/posts/${nextPost.slug}`}
          className="flex flex-1 flex-col items-end rounded border border-border-3 p-4 hover:bg-background-2"
        >
          <span className="text-xs text-text-4">다음 글</span>
          <span className="mt-1 text-sm font-medium text-text-1">{nextPost.title}</span>
        </Link>
      ) : (
        <div className="flex-1" />
      )}
    </nav>
  );
}
```

**Step 3: Create index**

```typescript
// src/features/post-detail/index.ts
export { PostContent } from "./ui/post-content";
export { PostNavigation } from "./ui/post-navigation";
```

**Step 4: Verify build**

Run: `pnpm compile:types && pnpm lint && pnpm build`
Expected: No errors

**Step 5: Commit**

```bash
git add src/features/post-detail/
git commit -m "feat: add PostContent and PostNavigation components"
```

### Task 4: 글 상세 페이지

**Files:**
- Create: `src/app/posts/[slug]/page.tsx`

**Step 1: Create post detail page (SSR)**

```tsx
// src/app/posts/[slug]/page.tsx
import { notFound } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import { fetchPostBySlug } from "@/entities/post";
import { PostContent, PostNavigation } from "@/features/post-detail";
import { ApiResponseError } from "@/shared/api";

interface PostPageProps {
  params: Promise<{ slug: string }>;
}

export default async function PostPage({ params }: PostPageProps) {
  const { slug } = await params;

  let data;
  try {
    data = await fetchPostBySlug(slug);
  } catch (error) {
    if (error instanceof ApiResponseError && error.statusCode === 404) {
      notFound();
    }
    throw error;
  }

  const { post, prevPost, nextPost } = data;
  const formattedDate = post.publishedAt
    ? new Date(post.publishedAt).toLocaleDateString("ko-KR", {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : null;

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <article>
        {/* Header */}
        <header className="mb-8">
          <h1 className="text-2xl font-bold text-text-1 sm:text-3xl">{post.title}</h1>
          <div className="mt-3 flex items-center gap-3 text-sm text-text-3">
            <Link
              href={`/categories/${post.category.slug}`}
              className="hover:text-primary-1"
            >
              {post.category.name}
            </Link>
            {formattedDate && <time>{formattedDate}</time>}
          </div>
          {post.tags.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {post.tags.map((tag) => (
                <Link
                  key={tag.id}
                  href={`/tags/${tag.slug}`}
                  className="rounded bg-background-3 px-2 py-1 text-xs text-text-3 hover:text-primary-1"
                >
                  {tag.name}
                </Link>
              ))}
            </div>
          )}
        </header>

        {/* Thumbnail */}
        {post.thumbnailUrl && (
          <div className="relative mb-8 aspect-video w-full overflow-hidden rounded">
            <Image
              src={post.thumbnailUrl}
              alt={post.title}
              fill
              sizes="(max-width: 768px) 100vw, 768px"
              className="object-cover"
              priority
            />
          </div>
        )}

        {/* Content */}
        <PostContent contentMd={post.contentMd} />
      </article>

      {/* Navigation */}
      <PostNavigation prevPost={prevPost} nextPost={nextPost} />
    </main>
  );
}
```

**Step 2: next/image remotePatterns 설정**

`next.config.js`에 API 서버 도메인 추가 (썸네일이 API 서버에서 서빙될 경우):

```javascript
// next.config.js
export default {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "github.com",
      },
      {
        protocol: "http",
        hostname: "localhost",
        port: "5500",
      },
    ],
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
};
```

**Step 3: Verify build**

Run: `pnpm compile:types && pnpm lint && pnpm build`
Expected: No errors

**Step 4: Commit**

```bash
git add src/app/posts/ next.config.js
git commit -m "feat: implement post detail page with markdown rendering"
```

### Task 5: 마크다운 스타일링

> `@tailwindcss/typography` 사용 여부에 따라 접근 방식 결정.

**Option A: @tailwindcss/typography 사용 (권장)**

```bash
pnpm add @tailwindcss/typography
```

`src/app-layer/style/index.css`에 추가:
```css
@plugin "@tailwindcss/typography";
```

**Option B: 커스텀 CSS**

`src/app-layer/style/markdown.css` 파일 생성 후 마크다운 HTML 요소에 직접 스타일 적용. `index.css`에서 import.

**Step 1:** 위 옵션 중 하나를 구현

**Step 2: Verify build**

Run: `pnpm compile:types && pnpm lint && pnpm build`
Expected: No errors

**Step 3: Commit**

```bash
git add -A
git commit -m "feat: add markdown content styling"
```

---

## Issue #8: 카테고리 네비게이션

> **GitHub:** `pyo-sh/pyosh-blog-fe#8`
> **Spec:** feature_spec.md §3.3
> **Server API:** `GET /api/categories` → `{ categories: CategoryTree[] }`
> **의존:** Issue #7 (PostCard, Pagination 재사용)

### Task 1: Category 엔티티

**Files:**
- Create: `src/entities/category/model.ts`
- Create: `src/entities/category/api.ts`
- Create: `src/entities/category/index.ts`

**Step 1: Create Category types**

```typescript
// src/entities/category/model.ts
export interface Category {
  id: number;
  parentId: number | null;
  name: string;
  slug: string;
  sortOrder: number;
  isVisible: boolean;
  createdAt: string;
  updatedAt: string;
  children: Category[];
}
```

**Step 2: Create Category API**

```typescript
// src/entities/category/api.ts
import { serverFetch } from "@/shared/api";
import type { Category } from "./model";

interface CategoriesResponse {
  categories: Category[];
}

export async function fetchCategories(
  cookieHeader?: string,
): Promise<Category[]> {
  const data = await serverFetch<CategoriesResponse>(
    "/api/categories",
    {},
    cookieHeader,
  );
  return data.categories;
}
```

**Step 3: Create index**

```typescript
// src/entities/category/index.ts
export type { Category } from "./model";
export { fetchCategories } from "./api";
```

**Step 4: Commit**

```bash
git add src/entities/category/
git commit -m "feat: add Category entity types and API"
```

### Task 2: 카테고리 네비게이션 위젯

**Files:**
- Create: `src/widgets/category-nav/ui/category-nav.tsx`
- Create: `src/widgets/category-nav/index.ts`

**Step 1: Create CategoryNav**

```tsx
// src/widgets/category-nav/ui/category-nav.tsx
import Link from "next/link";
import { cn } from "@/shared/lib/style-utils";
import type { Category } from "@/entities/category";

interface CategoryNavProps {
  categories: Category[];
  activeSlug?: string;
}

export function CategoryNav({ categories, activeSlug }: CategoryNavProps) {
  return (
    <nav className="flex flex-wrap gap-2">
      <Link
        href="/"
        className={cn(
          "rounded-full px-3 py-1.5 text-sm",
          !activeSlug
            ? "bg-primary-1 text-white"
            : "bg-background-3 text-text-2 hover:text-primary-1",
        )}
      >
        전체
      </Link>
      {categories.map((category) => (
        <Link
          key={category.id}
          href={`/categories/${category.slug}`}
          className={cn(
            "rounded-full px-3 py-1.5 text-sm",
            activeSlug === category.slug
              ? "bg-primary-1 text-white"
              : "bg-background-3 text-text-2 hover:text-primary-1",
          )}
        >
          {category.name}
        </Link>
      ))}
    </nav>
  );
}
```

**Step 2: Create index**

```typescript
// src/widgets/category-nav/index.ts
export { CategoryNav } from "./ui/category-nav";
```

**Step 3: Commit**

```bash
git add src/widgets/category-nav/
git commit -m "feat: add CategoryNav widget"
```

### Task 3: 카테고리별 글 목록 페이지

**Files:**
- Create: `src/app/categories/[slug]/page.tsx`

**Step 1: Create category page (SSR)**

```tsx
// src/app/categories/[slug]/page.tsx
import { notFound } from "next/navigation";
import { fetchPosts } from "@/entities/post";
import { fetchCategories } from "@/entities/category";
import { PostCard } from "@/features/post-list";
import { Pagination } from "@/shared/ui/libs";
import { CategoryNav } from "@/widgets/category-nav";

interface CategoryPageProps {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ page?: string }>;
}

export default async function CategoryPage({
  params,
  searchParams,
}: CategoryPageProps) {
  const { slug } = await params;
  const { page: pageParam } = await searchParams;
  const page = Number(pageParam) || 1;

  const categories = await fetchCategories();

  // slug에 해당하는 카테고리 찾기 (재귀 탐색)
  const findCategory = (cats: typeof categories, target: string): typeof categories[0] | null => {
    for (const cat of cats) {
      if (cat.slug === target) return cat;
      const found = findCategory(cat.children, target);
      if (found) return found;
    }
    return null;
  };

  const category = findCategory(categories, slug);
  if (!category) notFound();

  const { data: posts, meta } = await fetchPosts({
    page,
    categoryId: category.id,
  });

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <CategoryNav categories={categories} activeSlug={slug} />
      <h1 className="mt-6 text-xl font-bold text-text-1">{category.name}</h1>
      <section className="mt-4">
        {posts.length === 0 ? (
          <p className="py-16 text-center text-text-3">게시글이 없습니다.</p>
        ) : (
          posts.map((post) => <PostCard key={post.id} post={post} />)
        )}
      </section>
      <Pagination
        currentPage={page}
        totalPages={meta.totalPages}
        basePath={`/categories/${slug}`}
      />
    </main>
  );
}
```

**Step 2: (선택) 홈 페이지에도 CategoryNav 추가**

`src/app/page.tsx`에서 `fetchCategories()`를 호출하고 `<CategoryNav>` 삽입.

**Step 3: Verify build**

Run: `pnpm compile:types && pnpm lint && pnpm build`
Expected: No errors

**Step 4: Commit**

```bash
git add src/app/categories/ src/app/page.tsx
git commit -m "feat: implement category page with navigation"
```

---

## Phase 1 완료 체크리스트

- [ ] PaginatedResponse `total` 필드 수정
- [ ] Post 엔티티 (types + API)
- [ ] Pagination 컴포넌트
- [ ] PostCard 컴포넌트
- [ ] 홈 페이지 (SSR, 페이지네이션)
- [ ] 글로벌 loading/error/not-found
- [ ] 마크다운 의존성 설치
- [ ] 마크다운 렌더링 유틸리티 (shiki)
- [ ] PostContent + PostNavigation
- [ ] 글 상세 페이지 (SSR)
- [ ] next/image remotePatterns
- [ ] 마크다운 스타일링
- [ ] Category 엔티티 (types + API)
- [ ] CategoryNav 위젯
- [ ] 카테고리별 글 목록 페이지
