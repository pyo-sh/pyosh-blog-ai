# Phase 4: 부가 기능 — Implementation Plan

**Goal:** 카테고리 관리, 에셋 라이브러리, SEO, 검색, Admin 댓글/방명록 관리 구현

**Area:** client

**Architecture:** Admin 기능은 TanStack Query + clientMutate (CSRF). 검색은 SSR. SEO는 Next.js metadata API + 서버 sitemap/RSS 연동.

**Tech Stack:** Next.js 14 (App Router), TanStack Query, TailwindCSS v4

**References:**
- Feature spec: `docs/client/feature_spec.md` (sections 3.9, 4.5-4.8, 5.3)

**Prerequisites:**
- Phase 1-3 완료
- 서버 API 준비 완료: 카테고리 CRUD, 에셋 CRUD, `GET /api/admin/comments`, `GET /api/admin/guestbook`

**GitHub Issues:**
- #17 — 카테고리 관리 (Admin)
- #18 — 에셋 라이브러리 (Admin)
- #6 — SEO 최적화
- 검색 기능 — **이슈 미생성** (생성 필요)
- Admin 댓글/방명록 관리 — **이슈 미생성** (생성 필요)

---

## Issue #17: 카테고리 관리 (Admin)

> **Spec:** feature_spec.md §4.5
> **Server API:** `GET /api/categories?include_hidden=true`, `POST /api/categories`, `PATCH /api/categories/:id`, `PATCH /api/categories/order`, `DELETE /api/categories/:id`

### Task 1: Category Admin API

**Files:**
- Modify: `src/entities/category/api.ts`
- Modify: `src/entities/category/model.ts`
- Modify: `src/entities/category/index.ts`

**Step 1: Add admin types and API**

`src/entities/category/model.ts`에 추가:

```typescript
export interface CreateCategoryBody {
  name: string;
  parentId?: number | null;
  isVisible?: boolean;
}

export interface UpdateCategoryBody {
  name?: string;
  isVisible?: boolean;
}

export interface UpdateCategoryOrderBody {
  orders: { id: number; sortOrder: number }[];
}
```

`src/entities/category/api.ts`에 추가:

```typescript
import { clientFetch, clientMutate } from "@/shared/api";

export async function fetchCategoriesAdmin(): Promise<Category[]> {
  const data = await clientFetch<CategoriesResponse>(
    "/api/categories?include_hidden=true",
  );
  return data.categories;
}

export async function createCategory(body: CreateCategoryBody): Promise<Category> {
  const data = await clientMutate<{ category: Category }>("/api/categories", {
    method: "POST",
    body: JSON.stringify(body),
  });
  return data.category;
}

export async function updateCategory(
  id: number,
  body: UpdateCategoryBody,
): Promise<Category> {
  const data = await clientMutate<{ category: Category }>(`/api/categories/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
  return data.category;
}

export async function updateCategoryOrder(
  body: UpdateCategoryOrderBody,
): Promise<void> {
  await clientMutate<{ success: boolean }>("/api/categories/order", {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function deleteCategory(id: number): Promise<void> {
  await clientMutate<void>(`/api/categories/${id}`, { method: "DELETE" });
}
```

**Step 2: Commit**

```bash
git add src/entities/category/
git commit -m "feat: add admin category API functions"
```

### Task 2: 카테고리 관리 Feature

**Files:**
- Create: `src/features/category-manager/ui/category-tree.tsx`
- Create: `src/features/category-manager/ui/category-form-modal.tsx`
- Create: `src/features/category-manager/index.ts`

**Step 1: Create CategoryTree**

카테고리를 트리 구조로 시각화. 각 노드에 수정/삭제/순서변경 버튼.

```tsx
// src/features/category-manager/ui/category-tree.tsx
"use client";

import type { Category } from "@/entities/category";

interface CategoryTreeProps {
  categories: Category[];
  onEdit: (category: Category) => void;
  onDelete: (id: number) => void;
  depth?: number;
}

export function CategoryTree({
  categories,
  onEdit,
  onDelete,
  depth = 0,
}: CategoryTreeProps) {
  return (
    <ul className={depth > 0 ? "ml-6 border-l border-border-3 pl-4" : ""}>
      {categories.map((cat) => (
        <li key={cat.id} className="py-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className={`text-sm ${cat.isVisible ? "text-text-1" : "text-text-4 line-through"}`}>
                {cat.name}
              </span>
              <span className="text-xs text-text-4">({cat.slug})</span>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => onEdit(cat)}
                className="text-xs text-text-3 hover:text-primary-1"
              >
                수정
              </button>
              <button
                onClick={() => onDelete(cat.id)}
                className="text-xs text-text-3 hover:text-negative-1"
              >
                삭제
              </button>
            </div>
          </div>
          {cat.children.length > 0 && (
            <CategoryTree
              categories={cat.children}
              onEdit={onEdit}
              onDelete={onDelete}
              depth={depth + 1}
            />
          )}
        </li>
      ))}
    </ul>
  );
}
```

**Step 2: Create CategoryFormModal**

카테고리 생성/수정 모달. name, parentId, isVisible 입력.

```tsx
// src/features/category-manager/ui/category-form-modal.tsx
"use client";

import { useState, useEffect } from "react";
import type { Category, CreateCategoryBody } from "@/entities/category";

interface CategoryFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: CreateCategoryBody) => Promise<void>;
  category?: Category; // 수정 시
  allCategories: Category[];
}

export function CategoryFormModal({
  isOpen,
  onClose,
  onSubmit,
  category,
  allCategories,
}: CategoryFormModalProps) {
  const [name, setName] = useState(category?.name ?? "");
  const [parentId, setParentId] = useState<number | null>(category?.parentId ?? null);
  const [isVisible, setIsVisible] = useState(category?.isVisible ?? true);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (category) {
      setName(category.name);
      setParentId(category.parentId);
      setIsVisible(category.isVisible);
    } else {
      setName("");
      setParentId(null);
      setIsVisible(true);
    }
  }, [category]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await onSubmit({ name, parentId, isVisible });
      onClose();
    } finally {
      setLoading(false);
    }
  };

  // flat list for parent selector
  const flatten = (cats: Category[]): Category[] =>
    cats.flatMap((c) => [c, ...flatten(c.children)]);
  const flatCategories = flatten(allCategories).filter((c) => c.id !== category?.id);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md rounded bg-background-1 p-6 shadow-lg"
      >
        <h2 className="text-lg font-bold text-text-1">
          {category ? "카테고리 수정" : "카테고리 추가"}
        </h2>
        <div className="mt-4 space-y-3">
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="카테고리 이름"
            required
            className="w-full rounded border border-border-3 bg-background-1 px-3 py-2 text-sm text-text-1"
          />
          <select
            value={parentId ?? ""}
            onChange={(e) => setParentId(e.target.value ? Number(e.target.value) : null)}
            className="w-full rounded border border-border-3 bg-background-1 px-3 py-2 text-sm text-text-1"
          >
            <option value="">최상위 카테고리</option>
            {flatCategories.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
          <label className="flex items-center gap-2 text-sm text-text-2">
            <input
              type="checkbox"
              checked={isVisible}
              onChange={(e) => setIsVisible(e.target.checked)}
            />
            표시
          </label>
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded px-3 py-1.5 text-sm text-text-3"
          >
            취소
          </button>
          <button
            type="submit"
            disabled={loading}
            className="rounded bg-primary-1 px-4 py-1.5 text-sm text-white disabled:opacity-50"
          >
            {loading ? "저장 중..." : "저장"}
          </button>
        </div>
      </form>
    </div>
  );
}
```

**Step 3: Create index + page**

```typescript
// src/features/category-manager/index.ts
export { CategoryTree } from "./ui/category-tree";
export { CategoryFormModal } from "./ui/category-form-modal";
```

**Step 4: Create admin categories page**

```tsx
// src/app/dashboard/categories/page.tsx
"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchCategoriesAdmin,
  createCategory,
  updateCategory,
  deleteCategory,
  type Category,
} from "@/entities/category";
import { CategoryTree, CategoryFormModal } from "@/features/category-manager";

export default function AdminCategoriesPage() {
  const queryClient = useQueryClient();
  const [editTarget, setEditTarget] = useState<Category | undefined>();
  const [showForm, setShowForm] = useState(false);

  const { data: categories = [], isLoading } = useQuery({
    queryKey: ["admin", "categories"],
    queryFn: fetchCategoriesAdmin,
  });

  const createMutation = useMutation({
    mutationFn: createCategory,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "categories"] }),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, ...body }: { id: number; name?: string; isVisible?: boolean }) =>
      updateCategory(id, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "categories"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteCategory,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "categories"] }),
  });

  const handleSubmit = async (data: Parameters<typeof createCategory>[0]) => {
    if (editTarget) {
      await updateMutation.mutateAsync({ id: editTarget.id, ...data });
    } else {
      await createMutation.mutateAsync(data);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-text-1">카테고리 관리</h1>
        <button
          onClick={() => { setEditTarget(undefined); setShowForm(true); }}
          className="rounded bg-primary-1 px-4 py-2 text-sm text-white hover:opacity-90"
        >
          추가
        </button>
      </div>
      <div className="mt-6">
        {isLoading ? (
          <p className="text-text-3">로딩 중...</p>
        ) : (
          <CategoryTree
            categories={categories}
            onEdit={(cat) => { setEditTarget(cat); setShowForm(true); }}
            onDelete={(id) => {
              if (confirm("삭제하시겠습니까?")) deleteMutation.mutate(id);
            }}
          />
        )}
      </div>
      <CategoryFormModal
        isOpen={showForm}
        onClose={() => { setShowForm(false); setEditTarget(undefined); }}
        onSubmit={handleSubmit}
        category={editTarget}
        allCategories={categories}
      />
    </div>
  );
}
```

**Step 5: Verify & Commit**

```bash
pnpm compile:types && pnpm lint && pnpm build
git add src/features/category-manager/ src/app/dashboard/categories/ src/entities/category/
git commit -m "feat: implement admin category management"
```

---

## Issue #18: 에셋 라이브러리 (Admin)

> **Spec:** feature_spec.md §4.6
> **Server API:** `GET /api/assets?page=N`, `POST /api/assets/upload` (multipart), `DELETE /api/assets/:id`

### Task 1: Asset 엔티티

**Files:**
- Create: `src/entities/asset/model.ts`
- Create: `src/entities/asset/api.ts`
- Create: `src/entities/asset/index.ts`

**Step 1: Create types + API**

```typescript
// src/entities/asset/model.ts
export interface Asset {
  id: number;
  url: string;
  mimeType: string;
  sizeBytes: number;
  width: number;
  height: number;
  createdAt: string;
}
```

```typescript
// src/entities/asset/api.ts
import { clientFetch, clientMutate } from "@/shared/api";
import type { PaginatedResponse } from "@/shared/api";
import { getCsrfToken } from "@/shared/api";
import type { Asset } from "./model";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:5500";

export async function fetchAssets(
  page: number = 1,
): Promise<PaginatedResponse<Asset>> {
  return clientFetch<PaginatedResponse<Asset>>(`/api/assets?page=${page}`);
}

export async function uploadAssets(files: File[]): Promise<Asset[]> {
  const token = await getCsrfToken();
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));

  const response = await fetch(`${API_URL}/api/assets/upload`, {
    method: "POST",
    body: formData,
    credentials: "include",
    headers: {
      "x-csrf-token": token,
      // Content-Type은 FormData가 자동 설정하므로 명시하지 않음
    },
  });

  if (!response.ok) throw new Error("Upload failed");
  const data = await response.json();
  return data.assets;
}

export async function deleteAsset(id: number): Promise<void> {
  await clientMutate<void>(`/api/assets/${id}`, { method: "DELETE" });
}
```

```typescript
// src/entities/asset/index.ts
export type { Asset } from "./model";
export { fetchAssets, uploadAssets, deleteAsset } from "./api";
```

**Step 2: Commit**

```bash
git add src/entities/asset/
git commit -m "feat: add Asset entity types and API"
```

### Task 2: 에셋 라이브러리 Feature + 페이지

**Files:**
- Create: `src/features/asset-uploader/ui/asset-grid.tsx`
- Create: `src/features/asset-uploader/ui/upload-zone.tsx`
- Create: `src/features/asset-uploader/index.ts`
- Create: `src/app/dashboard/assets/page.tsx`

**Step 1: Create AssetGrid**

이미지 갤러리 그리드. URL 복사 + 삭제 기능.

```tsx
// src/features/asset-uploader/ui/asset-grid.tsx
"use client";

import type { Asset } from "@/entities/asset";

interface AssetGridProps {
  assets: Asset[];
  onDelete: (id: number) => void;
}

export function AssetGrid({ assets, onDelete }: AssetGridProps) {
  const copyUrl = (url: string, format: "plain" | "markdown") => {
    const text = format === "markdown" ? `![](${url})` : url;
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
      {assets.map((asset) => (
        <div key={asset.id} className="group relative overflow-hidden rounded border border-border-3">
          <img
            src={asset.url}
            alt=""
            className="aspect-square w-full object-cover"
          />
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-black/60 opacity-0 transition-opacity group-hover:opacity-100">
            <button
              onClick={() => copyUrl(asset.url, "plain")}
              className="rounded bg-white px-3 py-1 text-xs text-black"
            >
              URL 복사
            </button>
            <button
              onClick={() => copyUrl(asset.url, "markdown")}
              className="rounded bg-white px-3 py-1 text-xs text-black"
            >
              마크다운 복사
            </button>
            <button
              onClick={() => onDelete(asset.id)}
              className="rounded bg-negative-1 px-3 py-1 text-xs text-white"
            >
              삭제
            </button>
          </div>
          <div className="p-2 text-xs text-text-4">
            {(asset.sizeBytes / 1024).toFixed(0)}KB • {asset.width}×{asset.height}
          </div>
        </div>
      ))}
    </div>
  );
}
```

**Step 2: Create UploadZone**

드래그&드롭 + 파일 선택. max 5개, 10MB/개.

```tsx
// src/features/asset-uploader/ui/upload-zone.tsx
"use client";

import { useState, useRef, useCallback } from "react";

const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml"];
const MAX_FILES = 5;
const MAX_SIZE = 10 * 1024 * 1024; // 10MB

interface UploadZoneProps {
  onUpload: (files: File[]) => Promise<void>;
}

export function UploadZone({ onUpload }: UploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateFiles = (files: File[]): string | null => {
    if (files.length > MAX_FILES) return `최대 ${MAX_FILES}개까지 업로드 가능합니다.`;
    for (const file of files) {
      if (!ALLOWED_TYPES.includes(file.type)) return `허용되지 않는 파일 형식: ${file.name}`;
      if (file.size > MAX_SIZE) return `파일 크기 초과 (10MB): ${file.name}`;
    }
    return null;
  };

  const handleFiles = useCallback(async (fileList: FileList) => {
    const files = Array.from(fileList);
    const validationError = validateFiles(files);
    if (validationError) {
      setError(validationError);
      return;
    }
    setError("");
    setLoading(true);
    try {
      await onUpload(files);
    } catch {
      setError("업로드 실패");
    } finally {
      setLoading(false);
    }
  }, [onUpload]);

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(e) => { e.preventDefault(); setIsDragging(false); handleFiles(e.dataTransfer.files); }}
      onClick={() => inputRef.current?.click()}
      className={`cursor-pointer rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
        isDragging ? "border-primary-1 bg-primary-1/5" : "border-border-3 hover:border-primary-1"
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={ALLOWED_TYPES.join(",")}
        onChange={(e) => e.target.files && handleFiles(e.target.files)}
        className="hidden"
      />
      <p className="text-sm text-text-3">
        {loading ? "업로드 중..." : "이미지를 드래그하거나 클릭하여 업로드"}
      </p>
      <p className="mt-1 text-xs text-text-4">
        JPEG, PNG, GIF, WebP, SVG • 최대 5개 • 10MB/개
      </p>
      {error && <p className="mt-2 text-sm text-negative-1">{error}</p>}
    </div>
  );
}
```

**Step 3: Create index + page**

```typescript
// src/features/asset-uploader/index.ts
export { AssetGrid } from "./ui/asset-grid";
export { UploadZone } from "./ui/upload-zone";
```

에셋 관리 페이지:

```tsx
// src/app/dashboard/assets/page.tsx
"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchAssets, uploadAssets, deleteAsset } from "@/entities/asset";
import { AssetGrid, UploadZone } from "@/features/asset-uploader";

export default function AdminAssetsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["admin", "assets", page],
    queryFn: () => fetchAssets(page),
  });

  const uploadMutation = useMutation({
    mutationFn: uploadAssets,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "assets"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteAsset,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "assets"] }),
  });

  return (
    <div>
      <h1 className="text-2xl font-bold text-text-1">에셋 라이브러리</h1>
      <div className="mt-6">
        <UploadZone onUpload={(files) => uploadMutation.mutateAsync(files)} />
      </div>
      <div className="mt-6">
        {isLoading ? (
          <p className="text-text-3">로딩 중...</p>
        ) : (
          <AssetGrid
            assets={data?.data ?? []}
            onDelete={(id) => {
              if (confirm("삭제하시겠습니까?")) deleteMutation.mutate(id);
            }}
          />
        )}
      </div>
      {/* Client-side pagination */}
      {data && data.meta.totalPages > 1 && (
        <div className="mt-4 flex justify-center gap-2">
          {Array.from({ length: data.meta.totalPages }, (_, i) => i + 1).map((p) => (
            <button
              key={p}
              onClick={() => setPage(p)}
              className={`rounded px-3 py-1 text-sm ${
                p === page ? "bg-primary-1 text-white" : "text-text-2 hover:bg-background-2"
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
```

**Step 4: Verify & Commit**

```bash
pnpm compile:types && pnpm lint && pnpm build
git add src/entities/asset/ src/features/asset-uploader/ src/app/dashboard/assets/
git commit -m "feat: implement admin asset library with upload and gallery"
```

---

## Issue #6: SEO 최적화

> **Spec:** feature_spec.md §5.3
> **Server API:** `/sitemap.xml`, `/rss.xml`

### Task 1: 페이지별 메타데이터

**Files:**
- Modify: `src/app/layout.tsx` — 글로벌 기본 메타데이터
- Modify: `src/app/posts/[slug]/page.tsx` — 글별 동적 메타데이터
- Modify: `src/app/categories/[slug]/page.tsx` — 카테고리 메타데이터

**Step 1: Add global default metadata**

`src/app/layout.tsx`에서 `metadata` export 확인/보강:

```typescript
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: {
    default: "Pyosh Blog",
    template: "%s | Pyosh Blog",
  },
  description: "Pyosh의 개발 블로그",
  openGraph: {
    title: "Pyosh Blog",
    description: "Pyosh의 개발 블로그",
    type: "website",
    locale: "ko_KR",
  },
};
```

**Step 2: Add dynamic metadata to post page**

`src/app/posts/[slug]/page.tsx`에 `generateMetadata` 추가:

```typescript
import type { Metadata } from "next";

export async function generateMetadata({
  params,
}: PostPageProps): Promise<Metadata> {
  const { slug } = await params;
  try {
    const { post } = await fetchPostBySlug(slug);
    const description = post.contentMd.slice(0, 160).replace(/[#*`>\-\[\]]/g, "").trim();
    return {
      title: post.title,
      description,
      openGraph: {
        title: post.title,
        description,
        type: "article",
        publishedTime: post.publishedAt ?? undefined,
        ...(post.thumbnailUrl ? { images: [post.thumbnailUrl] } : {}),
      },
    };
  } catch {
    return { title: "글을 찾을 수 없습니다" };
  }
}
```

**Step 3: Sitemap/RSS 연동**

서버가 `/sitemap.xml`과 `/rss.xml`을 직접 서빙하므로, 클라이언트에서는:
- `<head>`에 RSS 링크 태그 추가 (layout.tsx):

```typescript
// layout.tsx metadata에 추가
alternates: {
  types: {
    "application/rss+xml": "http://localhost:5500/rss.xml",
  },
},
```

- 또는 Next.js의 `app/sitemap.ts`에서 서버 sitemap을 프록시/리다이렉트.

**Step 4: Verify & Commit**

```bash
pnpm compile:types && pnpm lint && pnpm build
git add src/app/
git commit -m "feat: add SEO metadata and Open Graph tags"
```

---

## 검색 기능 (이슈 미생성)

> **Spec:** feature_spec.md §3.9
> **Server API:** `GET /api/posts?q=keyword`
> **Note:** GitHub Issue를 먼저 생성해야 함

### Task 1: 검색 페이지

**Files:**
- Create: `src/app/search/page.tsx`

**Step 1: Create search page (SSR)**

```tsx
// src/app/search/page.tsx
import { fetchPosts } from "@/entities/post";
import { PostCard } from "@/features/post-list";
import { Pagination } from "@/shared/ui/libs";

interface SearchPageProps {
  searchParams: Promise<{ q?: string; page?: string }>;
}

export default async function SearchPage({ searchParams }: SearchPageProps) {
  const params = await searchParams;
  const query = params.q ?? "";
  const page = Number(params.page) || 1;

  if (!query) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-8">
        <h1 className="text-2xl font-bold text-text-1">검색</h1>
        <p className="mt-4 text-text-3">검색어를 입력하세요.</p>
      </main>
    );
  }

  const { data: posts, meta } = await fetchPosts({ page, q: query });

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-xl font-bold text-text-1">
        &quot;{query}&quot; 검색 결과
      </h1>
      <p className="mt-1 text-sm text-text-3">{meta.total}개의 결과</p>
      <section className="mt-4">
        {posts.length === 0 ? (
          <p className="py-16 text-center text-text-3">검색 결과가 없습니다.</p>
        ) : (
          posts.map((post) => <PostCard key={post.id} post={post} />)
        )}
      </section>
      <Pagination
        currentPage={page}
        totalPages={meta.totalPages}
        basePath="/search"
        queryParams={{ q: query }}
      />
    </main>
  );
}
```

**Step 2: Commit**

```bash
git add src/app/search/
git commit -m "feat: implement search results page"
```

### Task 2: 헤더에 검색 추가

**Files:**
- Create: `src/widgets/header/search-bar.tsx`
- Modify: `src/widgets/header/index.tsx`

**Step 1: Create SearchBar**

```tsx
// src/widgets/header/search-bar.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function SearchBar() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      router.push(`/search?q=${encodeURIComponent(query.trim())}`);
      setIsOpen(false);
      setQuery("");
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 text-text-2 hover:text-primary-1"
        aria-label="검색"
      >
        {/* Search icon SVG */}
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8" />
          <path d="M21 21l-4.35-4.35" />
        </svg>
      </button>
      {isOpen && (
        <form
          onSubmit={handleSubmit}
          className="absolute right-0 top-full mt-2 w-64 rounded border border-border-3 bg-background-1 p-2 shadow-lg"
        >
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="검색..."
            autoFocus
            className="w-full rounded border border-border-3 bg-background-1 px-3 py-1.5 text-sm text-text-1"
          />
        </form>
      )}
    </div>
  );
}
```

**Step 2: Add to header**

`src/widgets/header/index.tsx`에서 `<SearchBar />` 추가 (테마 버튼 옆).

**Step 3: Verify & Commit**

```bash
pnpm compile:types && pnpm lint && pnpm build
git add src/widgets/header/ src/app/search/
git commit -m "feat: add search bar to header and search results page"
```

---

## Admin 댓글/방명록 관리 (이슈 미생성)

> **Spec:** feature_spec.md §4.7, §4.8
> **Server API:** `GET /api/admin/comments`, `DELETE /api/admin/comments/:id`, `GET /api/admin/guestbook`, `DELETE /api/admin/guestbook/:id`
> **Note:** GitHub Issue를 먼저 생성해야 함

### Task 1: Admin Comment/Guestbook API

**Files:**
- Modify: `src/entities/comment/api.ts` — admin 함수 추가
- Modify: `src/entities/guestbook/api.ts` — admin 함수 추가

**Step 1: Add admin API functions**

`src/entities/comment/api.ts`에 추가:

```typescript
import type { PaginatedResponse } from "@/shared/api";

interface AdminCommentItem {
  id: number;
  postId: number;
  parentId: number | null;
  depth: number;
  body: string;
  isSecret: boolean;
  status: "active" | "deleted" | "hidden";
  author: CommentAuthor;
  replyToName: string | null;
  createdAt: string;
  updatedAt: string;
}

export async function fetchAdminComments(params: {
  page?: number;
  postId?: number;
}): Promise<PaginatedResponse<AdminCommentItem>> {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set("page", String(params.page));
  if (params.postId) searchParams.set("postId", String(params.postId));
  const query = searchParams.toString();
  return clientFetch<PaginatedResponse<AdminCommentItem>>(
    `/api/admin/comments${query ? `?${query}` : ""}`,
  );
}

export async function adminDeleteComment(id: number): Promise<void> {
  await clientMutate<void>(`/api/admin/comments/${id}`, { method: "DELETE" });
}
```

`src/entities/guestbook/api.ts`에 추가:

```typescript
export async function fetchAdminGuestbook(
  page: number = 1,
): Promise<PaginatedResponse<GuestbookEntry>> {
  return clientFetch<PaginatedResponse<GuestbookEntry>>(
    `/api/admin/guestbook?page=${page}`,
  );
}

export async function adminDeleteGuestbookEntry(id: number): Promise<void> {
  await clientMutate<void>(`/api/admin/guestbook/${id}`, { method: "DELETE" });
}
```

**Step 2: Commit**

```bash
git add src/entities/comment/ src/entities/guestbook/
git commit -m "feat: add admin comment and guestbook API functions"
```

### Task 2: Admin 댓글 관리 페이지

**Files:**
- Create: `src/app/dashboard/comments/page.tsx`

**Step 1: Create admin comments page**

TanStack Query로 목록 페칭, 필터(게시글별, 비밀 여부), 강제 삭제 기능. 비밀 댓글 내용 확인 가능.

```tsx
// src/app/dashboard/comments/page.tsx
"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchAdminComments, adminDeleteComment } from "@/entities/comment";

export default function AdminCommentsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["admin", "comments", page],
    queryFn: () => fetchAdminComments({ page }),
  });

  const deleteMutation = useMutation({
    mutationFn: adminDeleteComment,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "comments"] }),
  });

  return (
    <div>
      <h1 className="text-2xl font-bold text-text-1">댓글 관리</h1>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border-3 text-text-3">
            <tr>
              <th className="py-3">작성자</th>
              <th className="py-3">내용</th>
              <th className="py-3">비밀</th>
              <th className="py-3">작성일</th>
              <th className="py-3">작업</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={5} className="py-8 text-center text-text-3">로딩 중...</td></tr>
            ) : (
              data?.data.map((comment) => (
                <tr key={comment.id} className="border-b border-border-3">
                  <td className="py-3 text-text-1">{comment.author.name}</td>
                  <td className="max-w-xs truncate py-3 text-text-2">{comment.body}</td>
                  <td className="py-3">{comment.isSecret ? "🔒" : ""}</td>
                  <td className="py-3 text-text-4">
                    {new Date(comment.createdAt).toLocaleDateString("ko-KR")}
                  </td>
                  <td className="py-3">
                    <button
                      onClick={() => {
                        if (confirm("강제 삭제하시겠습니까?")) deleteMutation.mutate(comment.id);
                      }}
                      className="text-xs text-negative-1 hover:underline"
                    >
                      삭제
                    </button>
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
          {Array.from({ length: data.meta.totalPages }, (_, i) => i + 1).map((p) => (
            <button
              key={p}
              onClick={() => setPage(p)}
              className={`rounded px-3 py-1 text-sm ${
                p === page ? "bg-primary-1 text-white" : "text-text-2 hover:bg-background-2"
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
```

**Step 2: Verify & Commit**

```bash
pnpm compile:types && pnpm lint && pnpm build
git add src/app/dashboard/comments/
git commit -m "feat: implement admin comments management page"
```

### Task 3: Admin 방명록 관리 페이지

**Files:**
- Create: `src/app/dashboard/guestbook/page.tsx`

댓글 관리 페이지와 거의 동일한 구조. `fetchAdminGuestbook` + `adminDeleteGuestbookEntry` 사용.

**Step 1:** 위 댓글 관리 페이지와 동일 패턴으로 구현

**Step 2: Verify & Commit**

```bash
pnpm compile:types && pnpm lint && pnpm build
git add src/app/dashboard/guestbook/
git commit -m "feat: implement admin guestbook management page"
```

---

## 헤더 네비게이션 업데이트

Phase 1-4에서 추가된 페이지들을 헤더 네비게이션에 반영:

**Files:**
- Modify: `src/widgets/header/navigation.tsx`

Navigation items 업데이트:

```typescript
const navItems = [
  { href: "/", label: "홈" },
  { href: "/popular", label: "인기" },
  { href: "/tags", label: "태그" },
  { href: "/guestbook", label: "방명록" },
];
```

**Commit:**

```bash
git add src/widgets/header/navigation.tsx
git commit -m "feat: update header navigation with all pages"
```

---

## Phase 4 완료 체크리스트

- [ ] Category Admin API + 카테고리 관리 페이지
- [ ] Asset 엔티티 + 에셋 라이브러리 페이지
- [ ] SEO 메타데이터 (글로벌 + 동적 + RSS)
- [ ] 검색 페이지 + 헤더 검색바
- [ ] Admin 댓글 관리 페이지
- [ ] Admin 방명록 관리 페이지
- [ ] 헤더 네비게이션 업데이트

## 미생성 GitHub Issues

Phase 4 실행 전 다음 이슈를 생성해야 함:

1. **검색 기능** — 헤더 검색바 + `/search` 결과 페이지
2. **Admin 댓글/방명록 관리** — `/dashboard/comments`, `/dashboard/guestbook`
