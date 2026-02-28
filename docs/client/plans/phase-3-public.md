# Phase 3: 공개 부가 기능 — Implementation Plan

**Goal:** 댓글 시스템, 방명록, 태그, 인기 글, 조회수 기록 구현

**Area:** client

**Architecture:** 댓글/방명록은 게스트 전용 (OAuth 후속 버전). 서버 API 활용, 계층형 구조. 비밀 댓글 마스킹. 조회수는 useEffect + sessionStorage 중복 방지. 태그/인기 글은 SSR.

**Tech Stack:** Next.js 14 (App Router), TanStack Query, TailwindCSS v4

**References:**
- Feature spec: `docs/client/feature_spec.md` (sections 3.4-3.8)
- Server schemas: `server/src/routes/comments/comment.schema.ts`, `server/src/routes/guestbook/guestbook.schema.ts`

**Prerequisites:**
- Phase 1 완료 (Post 엔티티, Pagination, PostCard)
- Phase 2 완료 (CSRF 토큰, clientMutate)
- 서버 API 준비 완료: 댓글 CRUD, 방명록 CRUD, `GET /api/tags`, `GET /api/stats/popular`, `POST /api/stats/view`

---

## Issue #13: 댓글 시스템

> **GitHub:** `pyo-sh/pyosh-blog-fe#13`
> **Spec:** feature_spec.md §3.6
> **Server API:**
> - `GET /api/posts/:postId/comments` → `{ data: Comment[] }` (계층형)
> - `POST /api/posts/:postId/comments` → `{ data: Comment }` (게스트: guestName + guestEmail + guestPassword 필수)
> - `DELETE /api/comments/:id` + body `{ guestPassword }` → 204

### Task 1: Comment 엔티티

**Files:**
- Create: `src/entities/comment/model.ts`
- Create: `src/entities/comment/api.ts`
- Create: `src/entities/comment/index.ts`

**Step 1: Create Comment types**

```typescript
// src/entities/comment/model.ts
export interface CommentAuthor {
  type: "oauth" | "guest";
  id?: number;
  name: string;
  email?: string;
  avatarUrl?: string;
}

export interface Comment {
  id: number;
  postId: number;
  parentId: number | null;
  depth: number;
  body: string;
  isSecret: boolean;
  status: "active" | "deleted";
  author: CommentAuthor;
  replyToName: string | null;
  replies: Comment[];
  createdAt: string;
  updatedAt: string;
}

export interface CreateCommentGuestBody {
  body: string;
  parentId?: number;
  replyToCommentId?: number;
  isSecret?: boolean;
  guestName: string;
  guestEmail: string;
  guestPassword: string;
}

export interface DeleteCommentGuestBody {
  guestPassword: string;
}
```

**Step 2: Create Comment API**

```typescript
// src/entities/comment/api.ts
import { serverFetch, clientMutate } from "@/shared/api";
import type { Comment, CreateCommentGuestBody, DeleteCommentGuestBody } from "./model";

export async function fetchComments(
  postId: number,
  cookieHeader?: string,
): Promise<Comment[]> {
  const data = await serverFetch<{ data: Comment[] }>(
    `/api/posts/${postId}/comments`,
    {},
    cookieHeader,
  );
  return data.data;
}

export async function createComment(
  postId: number,
  body: CreateCommentGuestBody,
): Promise<Comment> {
  const data = await clientMutate<{ data: Comment }>(
    `/api/posts/${postId}/comments`,
    {
      method: "POST",
      body: JSON.stringify(body),
    },
  );
  return data.data;
}

export async function deleteComment(
  commentId: number,
  body: DeleteCommentGuestBody,
): Promise<void> {
  await clientMutate<void>(`/api/comments/${commentId}`, {
    method: "DELETE",
    body: JSON.stringify(body),
  });
}
```

**Step 3: Create index**

```typescript
// src/entities/comment/index.ts
export type { Comment, CommentAuthor, CreateCommentGuestBody, DeleteCommentGuestBody } from "./model";
export { fetchComments, createComment, deleteComment } from "./api";
```

**Step 4: Commit**

```bash
git add src/entities/comment/
git commit -m "feat: add Comment entity types and API"
```

### Task 2: CommentSection Feature

**Files:**
- Create: `src/features/comment-section/ui/comment-item.tsx`
- Create: `src/features/comment-section/ui/comment-form.tsx`
- Create: `src/features/comment-section/ui/comment-list.tsx`
- Create: `src/features/comment-section/index.ts`

**Step 1: Create CommentItem**

```tsx
// src/features/comment-section/ui/comment-item.tsx
"use client";

import { useState } from "react";
import type { Comment } from "@/entities/comment";

interface CommentItemProps {
  comment: Comment;
  onReply: (parentId: number, replyToCommentId: number) => void;
  onDelete: (commentId: number) => void;
}

export function CommentItem({ comment, onReply, onDelete }: CommentItemProps) {
  const isDeleted = comment.status === "deleted";
  const isSecret = comment.isSecret;

  const renderBody = () => {
    if (isDeleted) return <p className="italic text-text-4">삭제된 댓글입니다.</p>;
    if (isSecret) return <p className="italic text-text-4">비밀 댓글입니다.</p>;
    return <p className="text-text-2">{comment.body}</p>;
  };

  return (
    <div className={`py-4 ${comment.depth > 0 ? "ml-8 border-l-2 border-border-3 pl-4" : ""}`}>
      <div className="flex items-center gap-2 text-sm">
        <span className="font-medium text-text-1">{comment.author.name}</span>
        {comment.replyToName && (
          <span className="text-text-4">→ {comment.replyToName}</span>
        )}
        <time className="text-text-4">
          {new Date(comment.createdAt).toLocaleDateString("ko-KR")}
        </time>
      </div>
      <div className="mt-1">{renderBody()}</div>
      {!isDeleted && (
        <div className="mt-2 flex gap-3 text-xs text-text-4">
          {comment.depth === 0 && (
            <button
              onClick={() => onReply(comment.id, comment.id)}
              className="hover:text-primary-1"
            >
              답글
            </button>
          )}
          {comment.author.type === "guest" && (
            <button
              onClick={() => onDelete(comment.id)}
              className="hover:text-negative-1"
            >
              삭제
            </button>
          )}
        </div>
      )}
      {/* Replies */}
      {comment.replies?.map((reply) => (
        <CommentItem
          key={reply.id}
          comment={reply}
          onReply={onReply}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
}
```

**Step 2: Create CommentForm**

```tsx
// src/features/comment-section/ui/comment-form.tsx
"use client";

import { useState } from "react";

interface CommentFormProps {
  onSubmit: (data: {
    body: string;
    guestName: string;
    guestEmail: string;
    guestPassword: string;
    isSecret: boolean;
    parentId?: number;
    replyToCommentId?: number;
  }) => Promise<void>;
  parentId?: number;
  replyToCommentId?: number;
  onCancel?: () => void;
}

export function CommentForm({
  onSubmit,
  parentId,
  replyToCommentId,
  onCancel,
}: CommentFormProps) {
  const [body, setBody] = useState("");
  const [guestName, setGuestName] = useState("");
  const [guestEmail, setGuestEmail] = useState("");
  const [guestPassword, setGuestPassword] = useState("");
  const [isSecret, setIsSecret] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await onSubmit({
        body,
        guestName,
        guestEmail,
        guestPassword,
        isSecret,
        parentId,
        replyToCommentId,
      });
      setBody("");
      setGuestName("");
      setGuestEmail("");
      setGuestPassword("");
      setIsSecret(false);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3 rounded border border-border-3 p-4">
      <div className="grid grid-cols-3 gap-3">
        <input
          type="text"
          value={guestName}
          onChange={(e) => setGuestName(e.target.value)}
          placeholder="이름"
          required
          maxLength={50}
          className="rounded border border-border-3 bg-background-1 px-3 py-2 text-sm text-text-1"
        />
        <input
          type="email"
          value={guestEmail}
          onChange={(e) => setGuestEmail(e.target.value)}
          placeholder="이메일"
          required
          className="rounded border border-border-3 bg-background-1 px-3 py-2 text-sm text-text-1"
        />
        <input
          type="password"
          value={guestPassword}
          onChange={(e) => setGuestPassword(e.target.value)}
          placeholder="비밀번호"
          required
          minLength={4}
          className="rounded border border-border-3 bg-background-1 px-3 py-2 text-sm text-text-1"
        />
      </div>
      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder="댓글을 작성하세요..."
        required
        maxLength={2000}
        rows={3}
        className="w-full rounded border border-border-3 bg-background-1 px-3 py-2 text-sm text-text-1"
      />
      <div className="flex items-center justify-between">
        <label className="flex items-center gap-2 text-sm text-text-3">
          <input
            type="checkbox"
            checked={isSecret}
            onChange={(e) => setIsSecret(e.target.checked)}
          />
          비밀 댓글
        </label>
        <div className="flex gap-2">
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              className="rounded px-3 py-1.5 text-sm text-text-3 hover:bg-background-2"
            >
              취소
            </button>
          )}
          <button
            type="submit"
            disabled={loading}
            className="rounded bg-primary-1 px-4 py-1.5 text-sm text-white hover:opacity-90 disabled:opacity-50"
          >
            {loading ? "등록 중..." : "등록"}
          </button>
        </div>
      </div>
    </form>
  );
}
```

**Step 3: Create CommentList (orchestrator)**

```tsx
// src/features/comment-section/ui/comment-list.tsx
"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createComment, deleteComment, type Comment } from "@/entities/comment";
import { CommentItem } from "./comment-item";
import { CommentForm } from "./comment-form";

interface CommentListProps {
  postId: number;
  initialComments: Comment[];
}

export function CommentList({ postId, initialComments }: CommentListProps) {
  const queryClient = useQueryClient();
  const [comments, setComments] = useState(initialComments);
  const [replyTarget, setReplyTarget] = useState<{
    parentId: number;
    replyToCommentId: number;
  } | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null);
  const [deletePassword, setDeletePassword] = useState("");

  const handleSubmit = async (data: Parameters<typeof createComment>[1]) => {
    const newComment = await createComment(postId, {
      body: data.body,
      guestName: data.guestName,
      guestEmail: data.guestEmail,
      guestPassword: data.guestPassword,
      isSecret: data.isSecret,
      parentId: data.parentId,
      replyToCommentId: data.replyToCommentId,
    });
    // Re-fetch comments to update the tree
    const { fetchComments } = await import("@/entities/comment");
    const updated = await fetchComments(postId);
    setComments(updated);
    setReplyTarget(null);
  };

  const handleDelete = async (commentId: number) => {
    setDeleteTarget(commentId);
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    await deleteComment(deleteTarget, { guestPassword: deletePassword });
    const { fetchComments } = await import("@/entities/comment");
    const updated = await fetchComments(postId);
    setComments(updated);
    setDeleteTarget(null);
    setDeletePassword("");
  };

  return (
    <section className="mt-12 border-t border-border-3 pt-8">
      <h3 className="text-lg font-bold text-text-1">댓글 {comments.length}개</h3>

      {/* Comment list */}
      <div className="mt-4 divide-y divide-border-3">
        {comments.map((comment) => (
          <CommentItem
            key={comment.id}
            comment={comment}
            onReply={(parentId, replyToCommentId) =>
              setReplyTarget({ parentId, replyToCommentId })
            }
            onDelete={handleDelete}
          />
        ))}
      </div>

      {/* Reply form */}
      {replyTarget && (
        <div className="mt-4">
          <CommentForm
            onSubmit={handleSubmit}
            parentId={replyTarget.parentId}
            replyToCommentId={replyTarget.replyToCommentId}
            onCancel={() => setReplyTarget(null)}
          />
        </div>
      )}

      {/* Delete password modal */}
      {deleteTarget !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="rounded bg-background-1 p-6 shadow-lg">
            <p className="text-sm text-text-1">비밀번호를 입력하세요</p>
            <input
              type="password"
              value={deletePassword}
              onChange={(e) => setDeletePassword(e.target.value)}
              className="mt-2 w-full rounded border border-border-3 bg-background-1 px-3 py-2 text-sm text-text-1"
            />
            <div className="mt-4 flex justify-end gap-2">
              <button
                onClick={() => { setDeleteTarget(null); setDeletePassword(""); }}
                className="rounded px-3 py-1.5 text-sm text-text-3"
              >
                취소
              </button>
              <button
                onClick={confirmDelete}
                className="rounded bg-negative-1 px-3 py-1.5 text-sm text-white"
              >
                삭제
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main comment form */}
      <div className="mt-6">
        <CommentForm onSubmit={handleSubmit} />
      </div>
    </section>
  );
}
```

**Step 4: Create index**

```typescript
// src/features/comment-section/index.ts
export { CommentList } from "./ui/comment-list";
```

**Step 5: Verify build**

Run: `pnpm compile:types && pnpm lint && pnpm build`
Expected: No errors

**Step 6: Commit**

```bash
git add src/features/comment-section/
git commit -m "feat: add comment section with guest comments and secret comment masking"
```

### Task 3: 글 상세 페이지에 댓글 통합

**Files:**
- Modify: `src/app/posts/[slug]/page.tsx`

**Step 1: Add comments to post page**

`src/app/posts/[slug]/page.tsx`에서:
- `fetchComments(post.id)` 호출 추가 (SSR)
- `<CommentList postId={post.id} initialComments={comments} />` 렌더링

**Step 2: Verify build**

Run: `pnpm compile:types && pnpm lint && pnpm build`
Expected: No errors

**Step 3: Commit**

```bash
git add src/app/posts/
git commit -m "feat: integrate comments into post detail page"
```

---

## Issue #14: 방명록 페이지

> **GitHub:** `pyo-sh/pyosh-blog-fe#14`
> **Spec:** feature_spec.md §3.7
> **Server API:** `GET /api/guestbook?page=N`, `POST /api/guestbook`, `DELETE /api/guestbook/:id`

### Task 1: Guestbook 엔티티

**Files:**
- Create: `src/entities/guestbook/model.ts`
- Create: `src/entities/guestbook/api.ts`
- Create: `src/entities/guestbook/index.ts`

**Step 1: Create Guestbook types**

```typescript
// src/entities/guestbook/model.ts
import type { CommentAuthor } from "@/entities/comment";

export interface GuestbookEntry {
  id: number;
  parentId: number | null;
  body: string;
  isSecret: boolean;
  status: "active" | "deleted";
  author: CommentAuthor;
  replies: GuestbookEntry[];
  createdAt: string;
  updatedAt: string;
}

export interface CreateGuestbookBody {
  body: string;
  parentId?: number;
  isSecret?: boolean;
  guestName: string;
  guestEmail: string;
  guestPassword: string;
}

export interface DeleteGuestbookBody {
  guestPassword: string;
}
```

**Step 2: Create Guestbook API**

```typescript
// src/entities/guestbook/api.ts
import { serverFetch, clientMutate } from "@/shared/api";
import type { PaginatedResponse } from "@/shared/api";
import type { GuestbookEntry, CreateGuestbookBody, DeleteGuestbookBody } from "./model";

export async function fetchGuestbook(
  page: number = 1,
  cookieHeader?: string,
): Promise<PaginatedResponse<GuestbookEntry>> {
  return serverFetch<PaginatedResponse<GuestbookEntry>>(
    `/api/guestbook?page=${page}`,
    {},
    cookieHeader,
  );
}

export async function createGuestbookEntry(
  body: CreateGuestbookBody,
): Promise<GuestbookEntry> {
  const data = await clientMutate<{ data: GuestbookEntry }>("/api/guestbook", {
    method: "POST",
    body: JSON.stringify(body),
  });
  return data.data;
}

export async function deleteGuestbookEntry(
  id: number,
  body: DeleteGuestbookBody,
): Promise<void> {
  await clientMutate<void>(`/api/guestbook/${id}`, {
    method: "DELETE",
    body: JSON.stringify(body),
  });
}
```

**Step 3: Create index**

```typescript
// src/entities/guestbook/index.ts
export type { GuestbookEntry, CreateGuestbookBody, DeleteGuestbookBody } from "./model";
export { fetchGuestbook, createGuestbookEntry, deleteGuestbookEntry } from "./api";
```

**Step 4: Commit**

```bash
git add src/entities/guestbook/
git commit -m "feat: add Guestbook entity types and API"
```

### Task 2: 방명록 페이지

**Files:**
- Create: `src/features/guestbook-form/ui/guestbook-page-content.tsx`
- Create: `src/features/guestbook-form/index.ts`
- Create: `src/app/guestbook/page.tsx`

**Step 1: Create GuestbookPageContent (client component)**

댓글 시스템과 유사한 구조 (CommentForm 재사용 가능). 게스트 작성, 삭제(비밀번호), 페이지네이션.

```tsx
// src/features/guestbook-form/ui/guestbook-page-content.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  createGuestbookEntry,
  deleteGuestbookEntry,
  type GuestbookEntry,
} from "@/entities/guestbook";
import { CommentForm } from "@/features/comment-section/ui/comment-form";

interface GuestbookPageContentProps {
  entries: GuestbookEntry[];
  currentPage: number;
  totalPages: number;
}

export function GuestbookPageContent({
  entries: initialEntries,
  currentPage,
  totalPages,
}: GuestbookPageContentProps) {
  const router = useRouter();
  const [entries, setEntries] = useState(initialEntries);

  const handleSubmit = async (data: {
    body: string;
    guestName: string;
    guestEmail: string;
    guestPassword: string;
    isSecret: boolean;
  }) => {
    await createGuestbookEntry({
      body: data.body,
      guestName: data.guestName,
      guestEmail: data.guestEmail,
      guestPassword: data.guestPassword,
      isSecret: data.isSecret,
    });
    router.refresh();
  };

  // 삭제 로직은 댓글과 동일 패턴 (비밀번호 확인)

  return (
    <div>
      <div className="divide-y divide-border-3">
        {entries.map((entry) => (
          <div key={entry.id} className="py-4">
            <div className="flex items-center gap-2 text-sm">
              <span className="font-medium text-text-1">{entry.author.name}</span>
              <time className="text-text-4">
                {new Date(entry.createdAt).toLocaleDateString("ko-KR")}
              </time>
            </div>
            <p className="mt-1 text-text-2">
              {entry.isSecret ? "비밀 글입니다." : entry.body}
            </p>
          </div>
        ))}
      </div>
      <div className="mt-6">
        <CommentForm onSubmit={handleSubmit} />
      </div>
    </div>
  );
}
```

> **Note:** CommentForm을 방명록에서도 재사용. 필요시 props로 "댓글"/"방명록" 텍스트 전환.

**Step 2: Create guestbook page (SSR + client)**

```tsx
// src/app/guestbook/page.tsx
import { fetchGuestbook } from "@/entities/guestbook";
import { GuestbookPageContent } from "@/features/guestbook-form";
import { Pagination } from "@/shared/ui/libs";

interface GuestbookPageProps {
  searchParams: Promise<{ page?: string }>;
}

export default async function GuestbookPage({ searchParams }: GuestbookPageProps) {
  const params = await searchParams;
  const page = Number(params.page) || 1;
  const { data: entries, meta } = await fetchGuestbook(page);

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-2xl font-bold text-text-1">방명록</h1>
      <div className="mt-6">
        <GuestbookPageContent
          entries={entries}
          currentPage={page}
          totalPages={meta.totalPages}
        />
      </div>
      <Pagination currentPage={page} totalPages={meta.totalPages} basePath="/guestbook" />
    </main>
  );
}
```

**Step 3: Create feature index**

```typescript
// src/features/guestbook-form/index.ts
export { GuestbookPageContent } from "./ui/guestbook-page-content";
```

**Step 4: Verify & Commit**

```bash
pnpm compile:types && pnpm lint && pnpm build
git add src/entities/guestbook/ src/features/guestbook-form/ src/app/guestbook/
git commit -m "feat: implement guestbook page"
```

---

## Issue #15: 태그 페이지

> **GitHub:** `pyo-sh/pyosh-blog-fe#15`
> **Spec:** feature_spec.md §3.4
> **Server API:** `GET /api/tags` → `{ tags: [{ id, name, slug, postCount }] }`

### Task 1: Tag 엔티티

**Files:**
- Create: `src/entities/tag/model.ts`
- Create: `src/entities/tag/api.ts`
- Create: `src/entities/tag/index.ts`

**Step 1: Create types + API**

```typescript
// src/entities/tag/model.ts
export interface Tag {
  id: number;
  name: string;
  slug: string;
  postCount: number;
}
```

```typescript
// src/entities/tag/api.ts
import { serverFetch } from "@/shared/api";
import type { Tag } from "./model";

export async function fetchTags(cookieHeader?: string): Promise<Tag[]> {
  const data = await serverFetch<{ tags: Tag[] }>("/api/tags", {}, cookieHeader);
  return data.tags;
}
```

```typescript
// src/entities/tag/index.ts
export type { Tag } from "./model";
export { fetchTags } from "./api";
```

**Step 2: Commit**

```bash
git add src/entities/tag/
git commit -m "feat: add Tag entity types and API"
```

### Task 2: 태그 목록 + 태그별 글 목록 페이지

**Files:**
- Create: `src/app/tags/page.tsx`
- Create: `src/app/tags/[slug]/page.tsx`

**Step 1: Create tag list page**

```tsx
// src/app/tags/page.tsx
import Link from "next/link";
import { fetchTags } from "@/entities/tag";

export default async function TagsPage() {
  const tags = await fetchTags();

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-2xl font-bold text-text-1">태그</h1>
      <div className="mt-6 flex flex-wrap gap-3">
        {tags.map((tag) => (
          <Link
            key={tag.id}
            href={`/tags/${tag.slug}`}
            className="rounded-full bg-background-3 px-4 py-2 text-sm text-text-2 hover:text-primary-1"
          >
            {tag.name}
            <span className="ml-1 text-text-4">({tag.postCount})</span>
          </Link>
        ))}
      </div>
    </main>
  );
}
```

**Step 2: Create tag posts page**

```tsx
// src/app/tags/[slug]/page.tsx
import { fetchPosts } from "@/entities/post";
import { PostCard } from "@/features/post-list";
import { Pagination } from "@/shared/ui/libs";

interface TagPostsPageProps {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ page?: string }>;
}

export default async function TagPostsPage({ params, searchParams }: TagPostsPageProps) {
  const { slug } = await params;
  const { page: pageParam } = await searchParams;
  const page = Number(pageParam) || 1;

  const { data: posts, meta } = await fetchPosts({ page, tagSlug: slug });

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-xl font-bold text-text-1">
        태그: <span className="text-primary-1">{slug}</span>
      </h1>
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
        basePath={`/tags/${slug}`}
      />
    </main>
  );
}
```

**Step 3: Verify & Commit**

```bash
pnpm compile:types && pnpm lint && pnpm build
git add src/app/tags/
git commit -m "feat: implement tag list and tag posts pages"
```

---

## Issue #16: 인기 글 페이지

> **GitHub:** `pyo-sh/pyosh-blog-fe#16`
> **Spec:** feature_spec.md §3.5
> **Server API:** `GET /api/stats/popular?days=7&limit=10` → `{ data: [{ postId, slug, title, pageviews, uniques }] }`

### Task 1: PopularPost 타입 + API

**Files:**
- Modify: `src/entities/stat/model.ts`
- Modify: `src/entities/stat/api.ts`
- Modify: `src/entities/stat/index.ts`

**Step 1: Add types and API**

`src/entities/stat/model.ts`에 추가:

```typescript
export interface PopularPost {
  postId: number;
  slug: string;
  title: string;
  pageviews: number;
  uniques: number;
}
```

`src/entities/stat/api.ts`에 추가:

```typescript
export async function fetchPopularPosts(
  days: number = 7,
  cookieHeader?: string,
): Promise<PopularPost[]> {
  const data = await serverFetch<{ data: PopularPost[] }>(
    `/api/stats/popular?days=${days}`,
    {},
    cookieHeader,
  );
  return data.data;
}
```

**Step 2: Commit**

```bash
git add src/entities/stat/
git commit -m "feat: add popular posts API"
```

### Task 2: 인기 글 페이지

**Files:**
- Create: `src/app/popular/page.tsx`

**Step 1: Create popular posts page**

```tsx
// src/app/popular/page.tsx
import Link from "next/link";
import { fetchPopularPosts } from "@/entities/stat";

interface PopularPageProps {
  searchParams: Promise<{ days?: string }>;
}

export default async function PopularPage({ searchParams }: PopularPageProps) {
  const params = await searchParams;
  const days = Number(params.days) || 7;
  const posts = await fetchPopularPosts(days);

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-2xl font-bold text-text-1">인기 글</h1>

      {/* Period selector */}
      <div className="mt-4 flex gap-2">
        {[7, 30].map((d) => (
          <Link
            key={d}
            href={`/popular?days=${d}`}
            className={`rounded-full px-4 py-1.5 text-sm ${
              days === d
                ? "bg-primary-1 text-white"
                : "bg-background-3 text-text-2 hover:text-primary-1"
            }`}
          >
            {d}일
          </Link>
        ))}
      </div>

      {/* Posts */}
      <div className="mt-6 space-y-4">
        {posts.length === 0 ? (
          <p className="py-16 text-center text-text-3">데이터가 없습니다.</p>
        ) : (
          posts.map((post, index) => (
            <Link
              key={post.postId}
              href={`/posts/${post.slug}`}
              className="flex items-center gap-4 rounded border border-border-3 p-4 hover:bg-background-2"
            >
              <span className="text-lg font-bold text-text-4">{index + 1}</span>
              <div className="flex-1">
                <h3 className="font-medium text-text-1">{post.title}</h3>
              </div>
              <div className="text-right text-sm text-text-3">
                <p>{post.pageviews.toLocaleString()} views</p>
                <p>{post.uniques.toLocaleString()} visitors</p>
              </div>
            </Link>
          ))
        )}
      </div>
    </main>
  );
}
```

**Step 2: Verify & Commit**

```bash
pnpm compile:types && pnpm lint && pnpm build
git add src/app/popular/
git commit -m "feat: implement popular posts page"
```

---

## 조회수 기록 (feature_spec §3.8)

> Issue #5 글 상세 페이지에 통합. 별도 이슈 없음.
> **Server API:** `POST /api/stats/view` + body `{ postId }`

### Task 1: useViewCount 훅

**Files:**
- Create: `src/shared/hooks/use-view-count.ts`

**Step 1: Create hook**

```typescript
// src/shared/hooks/use-view-count.ts
"use client";

import { useEffect } from "react";
import { clientMutate } from "@/shared/api";

const VIEWED_KEY = "viewed_posts";

function getViewedPosts(): Set<number> {
  try {
    const raw = sessionStorage.getItem(VIEWED_KEY);
    return raw ? new Set(JSON.parse(raw)) : new Set();
  } catch {
    return new Set();
  }
}

function markAsViewed(postId: number): void {
  const viewed = getViewedPosts();
  viewed.add(postId);
  sessionStorage.setItem(VIEWED_KEY, JSON.stringify([...viewed]));
}

export function useViewCount(postId: number) {
  useEffect(() => {
    const viewed = getViewedPosts();
    if (viewed.has(postId)) return;

    clientMutate("/api/stats/view", {
      method: "POST",
      body: JSON.stringify({ postId }),
    })
      .then(() => markAsViewed(postId))
      .catch(() => {
        // 조회수 기록 실패는 무시
      });
  }, [postId]);
}
```

**Step 2: 글 상세 페이지에 통합**

글 상세 페이지에서 `useViewCount`를 호출할 클라이언트 래퍼 컴포넌트 생성:

```tsx
// src/features/post-detail/ui/view-counter.tsx
"use client";

import { useViewCount } from "@/shared/hooks/use-view-count";

export function ViewCounter({ postId }: { postId: number }) {
  useViewCount(postId);
  return null;
}
```

`src/app/posts/[slug]/page.tsx`에서 `<ViewCounter postId={post.id} />` 추가.

**Step 3: Verify & Commit**

```bash
pnpm compile:types && pnpm lint && pnpm build
git add src/shared/hooks/use-view-count.ts src/features/post-detail/ui/view-counter.tsx src/app/posts/
git commit -m "feat: add view count tracking with sessionStorage deduplication"
```

---

## Phase 3 완료 체크리스트

- [ ] Comment 엔티티 (types + API)
- [ ] CommentItem / CommentForm / CommentList 컴포넌트
- [ ] 글 상세 페이지에 댓글 통합
- [ ] Guestbook 엔티티 (types + API)
- [ ] 방명록 페이지
- [ ] Tag 엔티티 (types + API)
- [ ] 태그 목록 + 태그별 글 목록 페이지
- [ ] PopularPost API + 인기 글 페이지
- [ ] useViewCount 훅 + ViewCounter 컴포넌트
