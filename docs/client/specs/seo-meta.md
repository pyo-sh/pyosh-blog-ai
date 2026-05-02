# F-30: SEO 메타 (메타태그, OG, sitemap, RSS, robots.txt, canonical URL)

**상태:** DONE
**최종 수정:** 2026-05-02

---

## 1. 개요

모든 공개 페이지에 동적 메타데이터(title, description, OpenGraph, Twitter Card, canonical URL)를 제공하고, sitemap.xml, RSS 피드, robots.txt를 Next.js에서 생성한다. 관리 페이지(`/manage/*`)는 noindex 처리한다.

## 2. 배경 및 동기

현재 SEO 관련 구현 상태:

- 루트 `layout.tsx`에 정적 title("Pyosh Blog")과 favicon/manifest만 설정
- 각 페이지별 동적 메타데이터 없음 (title, description, OG 모두 미설정)
- canonical URL 미설정
- sitemap.xml, RSS는 서버(Fastify)에서 생성 중이나 URL 라우팅은 프론트엔드 소유
- robots.txt 미제공
- `metadataBase` 미설정으로 상대 경로 OG URL 변환 불가

## 3. 목표

- 모든 공개 페이지에 동적 title, description, OpenGraph, Twitter Card 메타데이터를 제공한다
- `metadataBase`와 `NEXT_PUBLIC_SITE_URL` 환경변수를 설정한다
- 각 페이지에 canonical URL을 `alternates.canonical`로 지정한다
- RSS 피드를 `alternates.types`로 선언하여 브라우저/피드 리더 자동 감지를 지원한다
- sitemap.xml, RSS 피드를 Next.js로 이전한다
- robots.txt를 Next.js `robots.ts`로 생성한다
- 관리 페이지(`/manage/*`)에 noindex를 적용한다
- Post 스키마에 `description` 필드를 추가한다

## 4. 비목표

- 동적 OG 이미지 생성 (`next/og`) - 와이어프레임 이후 결정
- 다국어 `hreflang` 설정 - 한국어 단일 블로그
- AMP 페이지
- 소셜 공유 버튼 UI

---

## 5. 상세 설계

### 5.1 환경 설정

#### `NEXT_PUBLIC_SITE_URL` 환경변수

```env
# .env.local
NEXT_PUBLIC_SITE_URL=https://blog.pyosh.dev
```

#### `metadataBase` 설정

루트 `layout.tsx`에 `metadataBase`를 설정한다.

```typescript
export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3000'),
  // ...기존 설정
};
```

### 5.2 Post 스키마 description 필드 추가

#### 서버 DB 스키마

```typescript
// post_tb에 description 컬럼 추가
description: varchar('description', { length: 300 }).default(null),
```

- nullable, 최대 300자
- 관리자가 글 작성 시 수동 입력 (선택)
- 비어 있으면 클라이언트에서 본문 자동 추출로 폴백

#### 클라이언트 폴백 로직

```typescript
function getPostDescription(post: Post): string {
  if (post.description) return post.description;
  return extractPlainText(post.contentMd, 160);
}
```

- `extractPlainText`: 마크다운에서 plain text 추출 후 160자 제한
- 현재 `post-list-item.tsx`에 유사 로직(200자)이 있으므로 공용 유틸로 분리

### 5.3 페이지별 메타데이터

#### 루트 레이아웃 (`layout.tsx`)

```typescript
export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3000'),
  title: {
    default: 'Pyosh Blog',
    template: '%s | Pyosh Blog',
  },
  description: 'Pyosh 개발 블로그',
  openGraph: {
    type: 'website',
    siteName: 'Pyosh Blog',
    locale: 'ko_KR',
  },
  twitter: {
    card: 'summary',
  },
  alternates: {
    types: {
      'application/rss+xml': '/rss.xml',
    },
  },
};
```

#### 페이지별 동적 메타데이터

| 페이지 | title | description | OG type | 메타데이터 방식 |
|---|---|---|---|---|
| 홈 (`/`) | "Pyosh Blog" (default) | 블로그 기본 설명 | `website` | 정적 `metadata` |
| 글 상세 (`/posts/[slug]`) | 글 제목 | `post.description` 또는 본문 160자 | `article` | `generateMetadata()` |
| 카테고리 (`/categories/[slug]`) | "{카테고리명} - 글 목록" | "{카테고리명} 카테고리의 글 목록" | `website` | `generateMetadata()` |
| 태그 (`/tags/[slug]`) | "#{태그명} - 글 목록" | "#{태그명} 태그가 포함된 글 목록" | `website` | `generateMetadata()` |
| 태그 목록 (`/tags`) | "태그 목록" | "모든 태그 목록" | `website` | 정적 `metadata` |
| 방명록 (`/guestbook`) | "방명록" | "방명록" | `website` | 정적 `metadata` |
| 검색 (`/search`) | "검색: {검색어}" | "'{검색어}' 검색 결과" | `website` | `generateMetadata()` |

#### 글 상세 `generateMetadata` 예시

```typescript
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const data = await fetchPostBySlug(slug);
  if (!data) return {};

  const { post } = data;
  const description = getPostDescription(post);

  return {
    title: post.title,
    description,
    openGraph: {
      type: 'article',
      title: post.title,
      description,
      publishedTime: post.publishedAt ?? undefined,
      modifiedTime: post.contentModifiedAt ?? post.publishedAt ?? undefined,
      tags: post.tags.map(t => t.name),
      ...(post.thumbnailUrl && { images: [post.thumbnailUrl] }),
    },
    twitter: {
      card: post.thumbnailUrl ? 'summary_large_image' : 'summary',
    },
    alternates: {
      canonical: `/posts/${post.slug}`,
    },
  };
}
```

### 5.4 Twitter Card 분기

Twitter 전용 태그를 별도로 관리하지 않고 OpenGraph 폴백을 활용한다. `card` 타입만 분기한다.

| 조건 | `twitter.card` |
|---|---|
| `thumbnailUrl` 있음 | `summary_large_image` |
| `thumbnailUrl` 없음 | `summary` |

- `twitter.title`, `twitter.description`, `twitter.image`는 설정하지 않음 - OpenGraph에서 자동 폴백

### 5.5 Canonical URL

각 페이지에 `alternates.canonical`을 설정한다. `metadataBase`가 있으므로 상대 경로로 지정.

| 페이지 | canonical |
|---|---|
| 홈 | `/` |
| 글 상세 | `/posts/{slug}` |
| 카테고리 | `/categories/{slug}` |
| 태그 | `/tags/{slug}` |
| 태그 목록 | `/tags` |
| 방명록 | `/guestbook` |
| 검색 | `/search?q={query}&filter={filter}` |
| 페이지네이션 | `?page=N` 파라미터 포함 |

- 페이지네이션: `?page=2` 등 페이지 파라미터를 canonical에 포함하여 각 페이지를 독립적으로 인덱싱
- 트래킹 파라미터(`utm_*`, `ref` 등)는 canonical에서 제외

### 5.6 Sitemap (서버 → Next.js 이전)

#### Next.js `sitemap.ts`

```typescript
// src/app/sitemap.ts
export default async function sitemap(): Promise<MetadataSitemap> {
  const posts = await fetchAllPublishedSlugs();
  const categories = await fetchVisibleCategories();

  return [
    // 정적 페이지
    { url: '/', changeFrequency: 'daily', priority: 1.0 },
    { url: '/guestbook', changeFrequency: 'weekly', priority: 0.5 },
    { url: '/tags', changeFrequency: 'weekly', priority: 0.5 },

    // 글 상세
    ...posts.map(post => ({
      url: `/posts/${post.slug}`,
      lastModified: post.updatedAt,
      changeFrequency: 'monthly' as const,
      priority: 0.8,
    })),

    // 카테고리
    ...categories.map(cat => ({
      url: `/categories/${cat.slug}`,
      changeFrequency: 'weekly' as const,
      priority: 0.6,
    })),
  ];
}
```

#### 서버 API 추가

sitemap 생성에 필요한 경량 엔드포인트를 추가한다.

| 메서드 | 경로 | 용도 | 응답 |
|---|---|---|---|
| GET | `/api/posts/slugs` | 발행된 글 slug 목록 | `{ slugs: [{ slug, updatedAt }] }` |

- 기존 글 목록 API를 사용할 수도 있으나, sitemap 전용으로 slug과 updatedAt만 반환하는 경량 엔드포인트가 효율적
- 카테고리 목록은 기존 API 사용

### 5.7 RSS 피드 (서버 → Next.js 이전)

#### Next.js Route Handler

```typescript
// src/app/rss.xml/route.ts
export async function GET() {
  const posts = await fetchRecentPosts(20);
  const xml = generateRssXml(posts);

  return new Response(xml, {
    headers: { 'Content-Type': 'application/rss+xml; charset=utf-8' },
  });
}
```

- 기존 서버 RSS 로직(마크다운 스트립, 220자 요약, 카테고리 태그)을 동일하게 구현
- `NEXT_PUBLIC_SITE_URL`을 사용하여 절대 URL 생성

### 5.8 robots.txt

#### Next.js `robots.ts`

```typescript
// src/app/robots.ts
export default function robots(): MetadataRoute.Robots {
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3000';

  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: '/manage/',
      },
    ],
    sitemap: `${siteUrl}/sitemap.xml`,
  };
}
```

### 5.9 관리 페이지 noindex

```typescript
// src/app/manage/layout.tsx
export const metadata: Metadata = {
  robots: {
    index: false,
    follow: false,
  },
};
```

### 5.10 SEO 유틸리티

#### 공용 유틸 분리

```typescript
// src/shared/lib/seo.ts

/** 마크다운에서 plain text를 추출하고 maxLength로 자른다 */
export function extractPlainText(markdown: string, maxLength: number): string;

/** Post description을 반환한다 (수동 입력 우선, 없으면 자동 추출) */
export function getPostDescription(post: Post): string;
```

- `extractPlainText`는 `post-list-item.tsx`의 기존 로직을 이동
- 마크다운 문법 제거: 헤딩(`#`), 링크(`[]()`), 이미지(`![]()`), 코드블록, 강조 등
- 줄바꿈을 공백으로 치환 후 trim

### 5.11 컴포넌트 구조 (FSD)

| 계층 | 파일 | 역할 |
|---|---|---|
| `app` | `layout.tsx` | 루트 메타데이터, `metadataBase` |
| `app` | `posts/[slug]/page.tsx` | 글 상세 `generateMetadata` |
| `app` | `categories/[slug]/page.tsx` | 카테고리 `generateMetadata` |
| `app` | `tags/[slug]/page.tsx` | 태그 `generateMetadata` |
| `app` | `search/page.tsx` | 검색 `generateMetadata` |
| `app` | `sitemap.ts` | 동적 sitemap 생성 |
| `app` | `rss.xml/route.ts` | RSS 피드 Route Handler |
| `app` | `robots.ts` | robots.txt 생성 |
| `app` | `manage/layout.tsx` | noindex 메타데이터 |
| `shared` | `lib/seo.ts` | `extractPlainText`, `getPostDescription` |
| `entities` | `post/api.ts` | `fetchAllPublishedSlugs` 추가 |

## 6. API 연동

| 메서드 | 경로 | 용도 | 변경 사항 |
|---|---|---|---|
| GET | `/api/posts/slugs` | 발행된 글 slug + updatedAt 목록 | 신규 (sitemap용) |
| GET | `/api/posts` | 최근 글 목록 | 기존 (RSS용) |
| GET | `/api/categories` | 카테고리 목록 | 기존 (sitemap용) |

### 서버 변경 사항

| 항목 | 설명 |
|---|---|
| DB 마이그레이션 | `post_tb`에 `description` 컬럼 추가 (varchar 300, nullable) |
| `PostDetailSchema` | `description` 필드 추가 |
| `CreatePostBodySchema` | `description` 필드 추가 (optional) |
| `UpdatePostBodySchema` | `description` 필드 추가 (optional) |
| 신규 엔드포인트 | `GET /api/posts/slugs` - sitemap용 경량 API |
| 기존 SEO 라우트 | `/sitemap.xml`, `/rss.xml` 제거 (프론트엔드로 이전) |

## 7. 수용 기준

- [ ] `NEXT_PUBLIC_SITE_URL` 환경변수가 설정되어 있다
- [ ] 루트 `layout.tsx`에 `metadataBase`가 설정되어 있다
- [ ] 루트 메타데이터에 title template, description, OG, RSS alternates가 있다
- [ ] 글 상세 페이지에 동적 title, description, OG(article), canonical이 있다
- [ ] 글 상세 OG에 publishedTime, modifiedTime, tags가 포함된다
- [ ] `post.thumbnailUrl` 유무에 따라 Twitter Card 타입이 분기된다
- [ ] `post.description`이 있으면 우선 사용, 없으면 본문 160자 자동 추출
- [ ] 카테고리/태그/검색 페이지에 동적 title, description, canonical이 있다
- [ ] 정적 페이지(태그 목록, 방명록, 인기 글)에 메타데이터가 있다
- [ ] 페이지네이션 페이지의 canonical에 `?page=N`이 포함된다
- [ ] `/sitemap.xml`이 모든 공개 URL을 포함한다
- [ ] `/rss.xml`이 최근 20개 글을 제공한다
- [ ] `/robots.txt`가 `/manage/`를 disallow하고 sitemap URL을 포함한다
- [ ] `/manage` 레이아웃에 `robots: { index: false, follow: false }`가 있다
- [ ] Post 스키마에 `description` 필드가 추가되어 있다
- [ ] `extractPlainText` 유틸이 공용으로 분리되어 있다

## 8. 에지 케이스

| 케이스 | 처리 |
|---|---|
| `NEXT_PUBLIC_SITE_URL` 미설정 | `http://localhost:3000` 폴백 |
| `post.description`과 `contentMd` 모두 비어 있음 | 빈 문자열 반환 (description 메타 태그 생략) |
| `thumbnailUrl`이 외부 URL | `metadataBase`와 무관하게 절대 URL 그대로 사용 |
| 비공개/임시저장 글 slug 직접 접근 | 404 반환, sitemap에 미포함 |
| 마크다운 첫 160자가 코드블록 | 코드블록 구문 제거 후 plain text 추출 |
| 글 slug에 특수문자 | URL 인코딩 처리 |
| sitemap 글 수가 매우 많을 때 (50,000+) | v1 범위 외, 필요 시 sitemap index 도입 |

## 9. 의존성

- F-01 홈 - 글 목록 (페이지 메타데이터)
- F-02 글 상세 (글 상세 메타데이터, OG article)
- F-33 환경 변수 분리 (`NEXT_PUBLIC_SITE_URL` 추가)

## 10. 미해결 사항

- 기본 OG 이미지: 와이어프레임 구상 이후 결정. 현재는 `thumbnailUrl` 없으면 OG 이미지 미설정.
- 서버 기존 SEO 라우트(`/sitemap.xml`, `/rss.xml`) 제거 시점: 프론트엔드 구현 완료 후 제거.
