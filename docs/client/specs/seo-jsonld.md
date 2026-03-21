# F-31: 구조화 데이터 (JSON-LD)

**상태:** DRAFT
**최종 수정:** 2026-03-21

---

## 1. 개요

검색엔진 리치 스니펫을 위해 JSON-LD 구조화 데이터를 주요 페이지에 삽입한다. `BlogPosting`, `BreadcrumbList`, `WebSite`+`SearchAction` 세 가지 스키마를 적용한다.

## 2. 배경 및 동기

현재 JSON-LD 구현이 전혀 없다. F-30에서 메타태그/OG를 통해 소셜 미디어 미리보기를 제공하지만, 검색엔진 리치 스니펫(발행일, 빵부스러기 경로, 사이트 검색 박스)을 위해서는 JSON-LD가 별도로 필요하다.

또한 현재 글 상세 API는 직속 카테고리(id, name, slug)만 반환하며 부모 카테고리 체인을 포함하지 않는다. BreadcrumbList에 카테고리 계층을 반영하려면 카테고리 경로 데이터가 필요하다.

## 3. 목표

- 글 상세 페이지에 `BlogPosting` JSON-LD를 삽입한다
- 글 상세, 카테고리, 태그 페이지에 `BreadcrumbList` JSON-LD를 삽입한다 (카테고리 계층 반영)
- 홈 페이지에 `WebSite` + `SearchAction` JSON-LD를 삽입한다
- 서버 API에서 카테고리 경로(부모 체인)를 제공한다

## 4. 비목표

- `Person` (저자) 스키마 - 단일 저자 블로그이므로 불필요
- `Organization` 스키마
- `FAQPage`, `HowTo` 등 콘텐츠 기반 스키마
- Google Search Console 연동

---

## 5. 상세 설계

### 5.1 BlogPosting (글 상세 페이지)

```jsonc
{
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "headline": "글 제목",
  "description": "글 description 또는 본문 160자 요약",
  "datePublished": "2026-03-15T09:00:00+09:00",
  "dateModified": "2026-03-20T14:00:00+09:00",
  "author": {
    "@type": "Person",
    "name": "Pyosh",
    "url": "https://github.com/pyo-sh"
  },
  "image": "https://blog.pyosh.dev/thumbnails/example.png",  // thumbnailUrl, 없으면 생략
  "url": "https://blog.pyosh.dev/posts/example-slug",
  "keywords": ["태그1", "태그2"],
  "articleSection": "카테고리명"
}
```

- `headline`: `post.title`
- `description`: F-30의 `getPostDescription()` 공유
- `datePublished`: `post.publishedAt`
- `dateModified`: `post.updatedAt`
- `author`: 이름 "Pyosh", URL은 GitHub 프로필. `Person` 스키마를 독립 엔티티로 분리하지 않고 인라인으로 최소한만 포함
- `image`: `post.thumbnailUrl` (없으면 필드 생략)
- `keywords`: `post.tags.map(t => t.name)`
- `articleSection`: `post.category.name`

### 5.2 BreadcrumbList

#### 카테고리 경로 데이터

현재 글 상세 API의 `PostCategory`는 `{ id, name, slug }`만 반환한다. BreadcrumbList에 카테고리 계층을 반영하려면 부모 체인이 필요하다.

**서버 API 변경:**

글 상세 응답의 `category` 필드에 `ancestors` 배열을 추가한다.

```typescript
interface PostCategory {
  id: number;
  name: string;
  slug: string;
  ancestors: { name: string; slug: string }[];  // 루트부터 부모까지 순서
}
```

예: 카테고리가 `개발 > Frontend > Next.js`이고 글이 `Next.js`에 속할 때:

```json
{
  "category": {
    "id": 5,
    "name": "Next.js",
    "slug": "nextjs",
    "ancestors": [
      { "name": "개발", "slug": "development" },
      { "name": "Frontend", "slug": "frontend" }
    ]
  }
}
```

#### 글 상세 페이지 BreadcrumbList

카테고리 계층을 모두 포함한다.

```jsonc
// 카테고리: 개발 > Frontend > Next.js, 글 제목: "SSR 가이드"
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    { "@type": "ListItem", "position": 1, "name": "홈", "item": "https://blog.pyosh.dev/" },
    { "@type": "ListItem", "position": 2, "name": "개발", "item": "https://blog.pyosh.dev/categories/development" },
    { "@type": "ListItem", "position": 3, "name": "Frontend", "item": "https://blog.pyosh.dev/categories/frontend" },
    { "@type": "ListItem", "position": 4, "name": "Next.js", "item": "https://blog.pyosh.dev/categories/nextjs" },
    { "@type": "ListItem", "position": 5, "name": "SSR 가이드" }
  ]
}
```

- 마지막 항목(현재 페이지)에는 `item` URL을 생략 (schema.org 권장)
- `ancestors` 배열 순서대로 루트 → 부모 → 직속 카테고리 → 글 제목

#### 카테고리 페이지 BreadcrumbList

카테고리 자체의 계층을 표시한다. 카테고리 페이지에서도 `ancestors` 데이터가 필요하므로 카테고리 API에도 경로 정보를 추가한다.

```jsonc
// /categories/nextjs (개발 > Frontend > Next.js)
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    { "@type": "ListItem", "position": 1, "name": "홈", "item": "https://blog.pyosh.dev/" },
    { "@type": "ListItem", "position": 2, "name": "개발", "item": "https://blog.pyosh.dev/categories/development" },
    { "@type": "ListItem", "position": 3, "name": "Frontend", "item": "https://blog.pyosh.dev/categories/frontend" },
    { "@type": "ListItem", "position": 4, "name": "Next.js" }
  ]
}
```

카테고리 페이지에서 ancestors를 구하는 방법:
- 이미 `GET /api/categories`가 전체 트리를 반환하므로, 클라이언트에서 트리를 탐색하여 현재 카테고리의 경로를 추출할 수 있다
- 또는 `GET /api/categories/:slug` 개별 엔드포인트에 `ancestors`를 포함 - 글 상세와 동일한 패턴

#### 태그 페이지 BreadcrumbList

태그는 계층이 없으므로 단순 구조.

```jsonc
// /tags/react
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    { "@type": "ListItem", "position": 1, "name": "홈", "item": "https://blog.pyosh.dev/" },
    { "@type": "ListItem", "position": 2, "name": "태그", "item": "https://blog.pyosh.dev/tags" },
    { "@type": "ListItem", "position": 3, "name": "react" }
  ]
}
```

### 5.3 WebSite + SearchAction (홈 페이지)

```jsonc
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "Pyosh Blog",
  "url": "https://blog.pyosh.dev/",
  "potentialAction": {
    "@type": "SearchAction",
    "target": {
      "@type": "EntryPoint",
      "urlTemplate": "https://blog.pyosh.dev/search?q={search_term_string}"
    },
    "query-input": "required name=search_term_string"
  }
}
```

- `NEXT_PUBLIC_SITE_URL`을 사용하여 절대 URL 생성 (F-30과 공유)
- Google이 사이트 규모에 따라 검색 박스 노출 여부를 결정

### 5.4 JSON-LD 렌더링 방식

Next.js App Router에서 Server Component 내 `<script>` 태그로 삽입한다.

```tsx
function JsonLd({ data }: { data: Record<string, unknown> }) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}
```

- 각 페이지의 Server Component에서 데이터를 구성하여 `<JsonLd>` 컴포넌트로 렌더링
- 한 페이지에 여러 JSON-LD 블록 가능 (BlogPosting + BreadcrumbList)

### 5.5 컴포넌트 구조 (FSD)

| 계층 | 파일 | 역할 |
|---|---|---|
| `app` | `page.tsx` | `WebSite` + `SearchAction` JSON-LD |
| `app` | `posts/[slug]/page.tsx` | `BlogPosting` + `BreadcrumbList` JSON-LD |
| `app` | `categories/[slug]/page.tsx` | `BreadcrumbList` JSON-LD |
| `app` | `tags/[slug]/page.tsx` | `BreadcrumbList` JSON-LD |
| `shared` | `ui/json-ld.tsx` | `JsonLd` 렌더링 컴포넌트 |
| `shared` | `lib/structured-data.ts` | JSON-LD 데이터 빌더 함수들 |

### 5.6 빌더 함수

```typescript
// shared/lib/structured-data.ts

export function buildBlogPostingJsonLd(post: Post, siteUrl: string): BlogPostingJsonLd;
export function buildBreadcrumbJsonLd(items: BreadcrumbItem[], siteUrl: string): BreadcrumbJsonLd;
export function buildWebSiteJsonLd(siteUrl: string): WebSiteJsonLd;
```

- `buildBlogPostingJsonLd`: Post 엔티티에서 JSON-LD 데이터 구성
- `buildBreadcrumbJsonLd`: `[{ name, href? }]` 배열을 BreadcrumbList로 변환
- `buildWebSiteJsonLd`: 정적 WebSite + SearchAction 구성

## 6. API 연동

| 메서드 | 경로 | 용도 | 변경 사항 |
|---|---|---|---|
| GET | `/api/posts/:slug` | 글 상세 | `category.ancestors` 필드 추가 |
| GET | `/api/categories` | 카테고리 트리 | 기존 (클라이언트에서 경로 추출) |

### 서버 변경 필요사항

| 항목 | 설명 |
|---|---|
| `PostCategory` 타입 | `ancestors: { name, slug }[]` 필드 추가 |
| `enrichPostWithDetails()` | 카테고리 조회 시 부모 체인을 재귀적으로 탐색하여 `ancestors` 구성 |
| `PostDetailSchema` | `category.ancestors` 스키마 추가 |

#### ancestors 조회 로직

```typescript
async function getCategoryAncestors(categoryId: number): Promise<{ name: string; slug: string }[]> {
  const ancestors: { name: string; slug: string }[] = [];
  let currentId: number | null = categoryId;

  while (currentId !== null) {
    const category = await db.query.categoryTable.findFirst({
      where: eq(categoryTable.id, currentId),
      columns: { id: true, parentId: true, name: true, slug: true },
    });
    if (!category) break;
    if (category.id !== categoryId) {
      ancestors.unshift({ name: category.name, slug: category.slug });
    }
    currentId = category.parentId;
  }

  return ancestors;
}
```

- 루트에서 부모까지 순서 (`unshift`로 역순 삽입)
- 직속 카테고리 자체는 `ancestors`에 포함하지 않음 (이미 `category.name`, `category.slug`로 제공)
- 카테고리 깊이가 제한적(3-4 depth)이므로 재귀 쿼리 성능 문제 없음

## 7. 수용 기준

- [ ] 글 상세 페이지에 `BlogPosting` JSON-LD가 삽입된다
- [ ] `BlogPosting`에 headline, description, datePublished, dateModified, author, keywords, articleSection이 포함된다
- [ ] `thumbnailUrl`이 있을 때만 `image` 필드가 포함된다
- [ ] 글 상세 페이지에 `BreadcrumbList` JSON-LD가 삽입된다
- [ ] BreadcrumbList가 카테고리 계층 구조를 반영한다 (예: 홈 > 개발 > Frontend > Next.js > 글 제목)
- [ ] 카테고리 페이지에 `BreadcrumbList` JSON-LD가 삽입된다 (계층 반영)
- [ ] 태그 페이지에 `BreadcrumbList` JSON-LD가 삽입된다 (홈 > 태그 > 태그명)
- [ ] 홈 페이지에 `WebSite` + `SearchAction` JSON-LD가 삽입된다
- [ ] SearchAction의 target URL이 `/search?q={search_term_string}` 형식이다
- [ ] 서버 글 상세 API가 `category.ancestors` 배열을 반환한다
- [ ] `JsonLd` 공용 컴포넌트가 `shared/ui/`에 분리되어 있다
- [ ] 빌더 함수가 `shared/lib/structured-data.ts`에 분리되어 있다
- [ ] Google Rich Results Test로 유효성을 검증한다

## 8. 에지 케이스

| 케이스 | 처리 |
|---|---|
| 카테고리가 루트(parentId=null)인 글 | ancestors 빈 배열, breadcrumb: 홈 > 카테고리명 > 글 제목 |
| 카테고리가 없는 글 | BreadcrumbList에서 카테고리 단계 생략, 홈 > 글 제목 |
| `publishedAt`이 null인 글 | `datePublished`에 `createdAt` 폴백 |
| `thumbnailUrl`이 null | `image` 필드 생략 (required 아님) |
| 태그가 없는 글 | `keywords` 필드 생략 |
| `NEXT_PUBLIC_SITE_URL` 미설정 | `http://localhost:3000` 폴백 (F-30과 동일) |
| JSON-LD 내 특수문자 (따옴표 등) | `JSON.stringify`가 자동 이스케이프 |

## 9. 의존성

- F-02 글 상세 (글 데이터, 카테고리 정보)
- F-30 SEO 메타 (`NEXT_PUBLIC_SITE_URL`, `getPostDescription()` 공유)

## 10. 미해결 사항

없음. 모든 사항 확정됨.
