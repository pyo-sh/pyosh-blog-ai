# F-02: 글 상세 (마크다운 렌더링, 코드 하이라이팅)

**상태:** DONE
**최종 수정:** 2026-05-02

---

## 1. 개요

게시글 상세 페이지. 마크다운 본문을 HTML로 렌더링하고, 코드 하이라이팅, 이전/다음 글 네비게이션, 조회수 기록, 댓글 섹션을 포함한다. GFM(GitHub Flavored Markdown) 지원, 코드블록 복사 버튼, 외부 링크 새 탭 열기를 추가한다.

## 2. 배경 및 동기

현재 글 상세 페이지가 구현되어 있으나 다음 개선이 필요하다:

- GFM(테이블, 체크박스, 취소선) 미지원
- 코드블록에 복사 버튼/언어 라벨 없음
- 마크다운 내 외부 링크가 같은 탭에서 열림
- 마크다운 내 이미지에 지연 로딩 미적용
- GFM 테이블의 반응형 처리 없음
- sanitizeSchema에 GFM 요소 허용 누락

## 3. 목표

- GFM 문법(테이블, 체크박스, 취소선)을 지원한다
- 코드블록에 복사 버튼과 언어 라벨을 표시한다
- 외부 링크를 새 탭에서 열리도록 한다
- 마크다운 내 이미지에 지연 로딩을 적용한다
- 테이블과 코드블록의 반응형 가로 스크롤을 보장한다
- 기존 구현의 안정성을 유지하면서 점진적으로 개선한다

## 4. 비목표

- Next.js `<Image>` 컴포넌트 적용 (HTML 문자열 구조상 불가)
- TOC 목차 (F-16에서 별도 개발)
- Heading anchor 링크
- 코드 하이라이팅 라이트 테마 (github-dark 단일 유지)
- 수학 수식 (KaTeX)
- `react-markdown` 전환

---

## 5. 상세 설계

### 5.1 페이지 구조

```
┌─────────────────────────────────────┐
│ [썸네일 이미지 (16:9)]               │
├─────────────────────────────────────┤
│ 카테고리 · 발행일 (· 수정: 날짜) · 조회수 │
│ 제목 (h1)                           │
│ #태그1 #태그2 #태그3                 │
├─────────────────────────────────────┤
│                                     │
│ 마크다운 본문                        │
│  - GFM 테이블 (가로 스크롤)           │
│  - 코드블록 (언어 라벨 + 복사 버튼)    │
│  - 체크박스, 취소선                   │
│  - 이미지 (lazy loading)             │
│  - 외부 링크 (새 탭)                 │
│                                     │
├─────────────────────────────────────┤
│ 관련 글 (가로 스크롤 카드 리스트)      │
│ [📷제목] [📷제목] [📷제목] [📷제목]  │
├─────────────────────────────────────┤
│ 댓글 섹션 (F-07, F-08)              │
└─────────────────────────────────────┘
```

- 썸네일 없는 글: 썸네일 영역 미표시, 바로 메타데이터 표시

- SSR (Server Component)
- 최대 너비: `max-w-5xl` (960px)
- 본문 컨테이너: `rounded-[2rem]`, `border border-border-3`, `bg-background-2`

### 5.2 마크다운 렌더링 파이프라인

현재 unified 기반 파이프라인에 플러그인을 추가한다.

```
마크다운 문자열
  │
  ▼ remarkParse          - 마크다운 → MDAST (트리)
  ▼ remarkGfm            - [추가] GFM 문법 파싱 (테이블, 체크박스, 취소선)
  ▼ remarkRehype         - MDAST → HAST (HTML 트리)
  ▼ rehypeShiki          - 코드블록 Shiki 하이라이팅 (github-dark)
  ▼ rehypeExternalLinks  - [추가] 외부 링크에 target="_blank" rel="noopener" 추가
  ▼ rehypeLazyImages     - [추가] <img>에 loading="lazy" decoding="async" 추가
  ▼ rehypeSanitize       - 위험한 HTML 제거 (allowlist 기반)
  ▼ rehypeStringify      - HAST → HTML 문자열
  │
  ▼ dangerouslySetInnerHTML → DOM
```

#### 변경 후 프로세서

```typescript
import remarkGfm from "remark-gfm";
import rehypeExternalLinks from "rehype-external-links";

const processor = unified()
  .use(remarkParse)
  .use(remarkGfm)
  .use(remarkRehype)
  .use(rehypeShiki, { theme: "github-dark" })
  .use(rehypeExternalLinks, {
    target: "_blank",
    rel: ["noopener", "noreferrer"],
  })
  .use(rehypeLazyImages)    // 커스텀 플러그인
  .use(rehypeSanitize, sanitizeSchema)
  .use(rehypeStringify)
  .freeze();
```

#### 커스텀 rehype 플러그인: rehypeLazyImages

```typescript
// <img> 노드에 loading="lazy" decoding="async" 속성 추가
function rehypeLazyImages() {
  return (tree: Node) => {
    visit(tree, "element", (node) => {
      if (node.tagName === "img") {
        node.properties.loading = "lazy";
        node.properties.decoding = "async";
      }
    });
  };
}
```

### 5.3 sanitizeSchema 확장

GFM 요소와 추가 속성을 허용 목록에 추가한다.

```typescript
const sanitizeSchema = {
  ...defaultSchema,
  attributes: {
    ...defaultSchema.attributes,
    // Shiki 코드 하이라이팅
    span: [...(defaultSchema.attributes?.span ?? []), "style", "className"],
    pre: [...(defaultSchema.attributes?.pre ?? []), "style", "className"],
    code: [...(defaultSchema.attributes?.code ?? []), "className"],
    // GFM 체크박스
    input: ["type", "checked", "disabled"],
    // 외부 링크
    a: [...(defaultSchema.attributes?.a ?? []), "target", "rel"],
    // 이미지 지연 로딩
    img: [...(defaultSchema.attributes?.img ?? []), "loading", "decoding"],
  },
  tagNames: [
    ...(defaultSchema.tagNames ?? []),
    "input",   // GFM 체크박스
    "del",     // GFM 취소선
  ],
};
```

### 5.4 코드블록 복사 버튼 + 언어 라벨

HTML 문자열 구조를 유지하면서 클라이언트 래퍼 컴포넌트로 구현한다.

#### 구현 방식

`PostContent`를 서버 컴포넌트(마크다운 렌더링) + 클라이언트 래퍼(복사 버튼 삽입)로 분리한다.

```
PostContent (Server Component)
  └─ renderMarkdown() → HTML 문자열
  └─ CodeBlockEnhancer (Client Component)
       └─ useEffect로 DOM에서 <pre> 블록 탐색
       └─ 각 <pre>에 언어 라벨 + 복사 버튼 삽입
```

#### CodeBlockEnhancer

```typescript
"use client";

export function CodeBlockEnhancer({ children }: PropsWithChildren) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const preBlocks = container.querySelectorAll("pre");
    preBlocks.forEach((pre) => {
      // 언어 감지: <code class="language-typescript"> → "typescript"
      const code = pre.querySelector("code");
      const lang = code?.className?.match(/language-(\w+)/)?.[1];

      // 헤더 바 삽입 (언어 라벨 + 복사 버튼)
      const header = createCodeHeader(lang, pre);
      pre.insertBefore(header, pre.firstChild);
    });
  }, []);

  return <div ref={containerRef}>{children}</div>;
}
```

#### 코드블록 UI

```
┌─ typescript ──────────── [📋 복사] ─┐
│ const greeting = "Hello";           │
│ console.log(greeting);              │
└─────────────────────────────────────┘
```

- 언어 라벨: 좌상단, `text-body-xs`, `text-text-4`
- 복사 버튼: 우상단, 클릭 시 `navigator.clipboard.writeText()` + "복사됨" 피드백 (1.5초)
- 헤더 배경: 코드블록과 동일 (`bg-background-2`)

### 5.5 GFM 테이블 반응형

마크다운 내 `<table>`이 모바일에서 레이아웃을 깨지 않도록 가로 스크롤 래퍼를 적용한다.

#### CSS 처리 (typography.css)

```css
.markdown-content table {
  display: block;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}
```

또는 rehype 플러그인으로 `<table>`을 `<div class="table-wrapper">` 래퍼로 감쌀 수도 있다. CSS 처리가 더 단순하므로 CSS 방식을 우선 사용한다.

#### 테이블 스타일 보강

```css
.markdown-content table {
  width: 100%;
  border-collapse: collapse;
}

.markdown-content th {
  background-color: var(--background3);
  font-weight: 600;
  text-align: left;
}

.markdown-content th,
.markdown-content td {
  border: 1px solid var(--border3);
  padding: 0.5rem 0.75rem;
}
```

### 5.6 외부 링크 처리

`rehype-external-links` 플러그인이 호스트가 다른 `<a>` 태그에 자동으로 `target="_blank"` + `rel="noopener noreferrer"`를 추가한다.

- 내부 링크 (같은 호스트): 변경 없음, 같은 탭
- 외부 링크 (다른 호스트): 새 탭, `noopener`로 보안 확보

### 5.7 이미지 지연 로딩

커스텀 `rehypeLazyImages` 플러그인이 모든 `<img>`에 적용:

- `loading="lazy"`: 뷰포트 근처까지 스크롤해야 로드
- `decoding="async"`: 이미지 디코딩이 메인 스레드를 블로킹하지 않음

### 5.8 관련 글

본문 하단에 가로 스크롤 카드 리스트로 관련 글을 표시한다.

```
관련 글
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
│ 썸네일 │ │ 썸네일 │ │ 썸네일 │ │ 썸네일 │ │ 썸네일 │  → 가로 스크롤
│ 제목   │ │ 제목   │ │ 제목   │ │ 제목   │ │ 제목   │
└──────┘ └──────┘ └──────┘ └──────┘ └──────┘
```

- 카드 너비: `180px`, 고정
- 썸네일: `aspect-ratio: 16/10`, `overflow-hidden`, `rounded-lg`
- 제목: `line-clamp-2`, `text-xs font-semibold`
- 카드 호버: `translateY(-3px)` + `box-shadow` + 썸네일 `scale(1.05)`
- 가로 스크롤: `overflow-x: auto`, `scroll-snap-type: x mandatory`, 스크롤바 숨김
- 관련 글 선정: 같은 카테고리의 최신 글 최대 5개 (서버에서 조회)
- 카테고리 미설정 시: 관련 글 컴포넌트를 렌더링하지 않는다 - API 요청 자체가 발생하지 않음
- 관련 글이 없으면 (같은 카테고리 글이 없음) 섹션 미표시

### 5.9 코드블록 가로 스크롤 (모바일)

현재 `overflow-x: auto`가 있으나, 코드블록이 부모 컨테이너를 넘지 않도록 `max-width` 제한을 추가한다.

```css
.markdown-content pre {
  overflow-x: auto;
  max-width: 100%;
}

.markdown-content pre code {
  display: block;
  min-width: max-content;
}
```

### 5.10 데이터 흐름

```
PostDetailPage (Server Component)
  ├─ fetchPostBySlug(slug) → GET /api/posts/:slug
  │   └─ 응답: { post, relatedPosts }
  ├─ fetchComments(postId) → GET /api/posts/:postId/comments
  ├─ getCurrentViewer() → GET /api/auth/me (쿠키 기반)
  │
  ├─ PostContent → renderMarkdown(contentMd) → HTML
  │   └─ CodeBlockEnhancer (Client) → 복사 버튼/언어 라벨 삽입
  ├─ ViewCounter (Client) → POST /api/stats/view (세션 중복 방지)
  ├─ RelatedPosts → 관련 글 가로 카드 리스트
  └─ CommentList (Client) → 댓글 목록 + 작성 폼
```

### 5.11 컴포넌트 구조 (FSD)

| 계층 | 파일 | 역할 |
|---|---|---|
| `app` | `posts/[slug]/page.tsx` | 페이지 컴포넌트 (SSR) |
| `features` | `post-detail/ui/post-content.tsx` | 마크다운 렌더링 서버 컴포넌트 |
| `features` | `post-detail/ui/code-block-enhancer.tsx` | 코드블록 복사/라벨 클라이언트 컴포넌트 |
| `features` | `post-detail/ui/related-posts.tsx` | 관련 글 가로 카드 리스트 |
| `features` | `post-detail/ui/view-counter.tsx` | 조회수 기록 클라이언트 컴포넌트 |
| `features` | `comment-section/` | 댓글 목록/작성/삭제 (F-07, F-08) |
| `shared` | `lib/markdown.ts` | unified 마크다운 프로세서 |
| `app-layer` | `style/typography.css` | 마크다운 prose 스타일 |

## 6. API 연동

| 메서드 | 경로 | 용도 |
|---|---|---|
| GET | `/api/posts/:slug` | 글 상세 + 관련 글 |
| GET | `/api/posts/:postId/comments` | 댓글 목록 |
| GET | `/api/auth/me` | 현재 사용자 (댓글 작성자 식별) |
| POST | `/api/stats/view` | 조회수 기록 |

## 7. 수용 기준

- [ ] 발행일(`publishedAt`)이 표시된다
- [ ] `contentModifiedAt`이 있으면 "수정: {날짜}"가 추가로 표시된다
- [ ] 마크다운 본문이 HTML로 올바르게 렌더링된다
- [ ] GFM 테이블이 올바르게 표시되고 모바일에서 가로 스크롤된다
- [ ] GFM 체크박스가 체크/미체크 상태로 표시된다 (읽기 전용)
- [ ] GFM 취소선(`~~text~~`)이 올바르게 표시된다
- [ ] 코드블록에 Shiki `github-dark` 테마 하이라이팅이 적용된다
- [ ] 코드블록 상단에 언어 라벨이 표시된다
- [ ] 코드블록 복사 버튼 클릭 시 코드가 클립보드에 복사되고 "복사됨" 피드백이 표시된다
- [ ] 외부 링크가 새 탭에서 열리며 `rel="noopener noreferrer"`가 적용된다
- [ ] 마크다운 내 이미지에 `loading="lazy"` `decoding="async"`가 적용된다
- [ ] 관련 글이 가로 스크롤 카드 리스트로 표시된다 (최대 5개)
- [ ] 카테고리 미설정 글에서는 관련 글 컴포넌트가 렌더링되지 않고, API 요청도 발생하지 않는다
- [ ] 모바일에서 코드블록이 페이지 레이아웃을 깨지 않고 가로 스크롤된다
- [ ] rehypeSanitize로 XSS 공격이 차단된다
- [ ] 다크모드 자동 적용 (typography.css 시맨틱 토큰)
- [ ] 접근성: 이미지 alt 텍스트, 시맨틱 마크업 (A-01 참조)
- [ ] Storybook story 작성 (F-38 참조)

## 8. 에지 케이스

| 케이스 | 처리 |
|---|---|
| 존재하지 않는 slug | 서버에서 404 → `notFound()` 호출 |
| 마크다운 본문 없음 | 빈 `<div>` 렌더링 |
| 언어 미지정 코드블록 | 하이라이팅 없이 plain text, 언어 라벨 미표시 |
| 매우 긴 코드라인 | `overflow-x: auto`로 가로 스크롤 |
| 마크다운 내 `<script>` 태그 | rehypeSanitize가 제거 |
| 외부 이미지 URL 깨짐 | 브라우저 기본 깨진 이미지 아이콘 |
| 썸네일 없는 글 | 썸네일 영역 미표시, 바로 메타데이터 표시 |
| 카테고리 미설정 글 | 관련 글 컴포넌트 미렌더링 (API 미호출) |
| 관련 글 없음 (같은 카테고리 글이 없음) | 관련 글 섹션 미표시 |
| 댓글 로드 실패 | 에러 메시지 표시, 글 본문은 정상 표시 |
| 클립보드 API 미지원 브라우저 | 복사 버튼 숨김 또는 폴백 처리 |

## 9. 의존성

- F-01 홈 - 글 목록 (글 데이터 구조 공유)

## 10. 미해결 사항

없음. 모든 사항 확정됨.
