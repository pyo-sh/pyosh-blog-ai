# F-16: 목차 (TOC)

**상태:** DONE
**최종 수정:** 2026-05-02

---

## 1. 개요

글 상세 페이지(F-02)에서 사이드바(F-39) 최상단에 목차(Table of Contents)를 표시한다. 마크다운 본문의 h1/h2/h3 heading을 추출하여 계층적으로 표시하고, 클릭 시 해당 섹션으로 스크롤한다. 모바일에서는 기본 접힌 상태로 제공한다.

## 2. 배경 및 동기

긴 글에서 전체 구조를 파악하고 원하는 섹션으로 빠르게 이동할 수 있는 목차가 필요하다. F-39 사이드바의 2컬럼 레이아웃을 활용하여 글 상세 페이지에서만 사이드바 최상단에 TOC를 배치한다.

## 3. 목표

- 글 상세 페이지 사이드바 최상단에 TOC를 표시한다
- h1/h2/h3 heading을 계층적으로 표시한다
- heading에 anchor ID를 부여하여 클릭 시 스크롤 + URL `#anchor` 지원
- 모바일에서 기본 접힌 상태로 제공한다
- heading이 없는 글에서는 TOC를 표시하지 않는다
- TOC 접기/펼치기를 지원한다

## 4. 비목표

- 스크롤 스파이 (현재 읽는 섹션 하이라이팅)
- h4 이하 heading 표시
- TOC 위치 커스터마이징 (사이드바 고정)
- 자동 번호 매기기

---

## 5. 상세 설계

### 5.1 TOC 표시 조건

| 조건 | TOC 표시 |
|---|---|
| 글 상세 페이지 + heading 1개 이상 | 표시 |
| 글 상세 페이지 + heading 0개 | 미표시 |
| 글 상세 외 페이지 (홈, 카테고리 등) | 미표시 |

### 5.2 사이드바 내 배치

글 상세 페이지에서 사이드바 섹션 순서:

| 순서 | 섹션 | 비고 |
|---|---|---|
| 1 | **목차 (TOC)** | 글 상세에서만 표시 |
| 2 | 최근글 / 인기글 탭 | F-39 기존 |
| 3 | 분류 (카테고리) | F-39 기존 |
| 4 | 태그 | F-39 기존 |
| 5 | 블로그 조회수 | F-39 기존 |

### 5.3 TOC UI

#### 데스크톱 (기본 펼침)

```
┌─ 목차 ──────────────── [▲] ┐
│                              │
│  소개                        │
│  배경                        │
│  구현                        │
│    설정                      │  ← h2 들여쓰기
│    코드                      │
│      상세 코드               │  ← h3 들여쓰기
│  결론                        │
│                              │
└──────────────────────────────┘
```

#### 모바일 (기본 접힘)

```
┌─ 목차 ──────────────── [▼] ┐
└──────────────────────────────┘
```

클릭 시 펼침:

```
┌─ 목차 ──────────────── [▲] ┐
│  소개                        │
│  배경                        │
│  ...                         │
└──────────────────────────────┘
```

#### 스타일

사이드바의 다른 섹션과 동일한 톤으로 배경/테두리 박스 없이 미니멀하게 표시한다.

| 요소 | 스타일 |
|---|---|
| 섹션 타이틀 | 사이드바 공통 헤더 (`.sidebar-section-title`): `text-xs`, `font-bold`, `uppercase`, `letter-spacing`, `text-text-4`, 아이콘 포함 |
| 접기/펼치기 아이콘 | Solar `alt-arrow-up-linear`, `text-text-4` |
| 항목 리스트 | `border-left: 2px solid border-4`, `pl-3` |
| h1 항목 | `text-xs`, `font-medium`, `text-text-3`, `pl-0` |
| h2 항목 | `text-xs`, `font-medium`, `text-text-3`, `pl-2.5` |
| h3 항목 | `text-[11px]`, `text-text-4`, `pl-5` |
| hover | `text-primary-1`, `transition-colors` |
| 컨테이너 | 배경/테두리 없음, 사이드바 섹션 구분선만 사용 |

### 5.4 heading anchor ID 부여

마크다운 렌더링 파이프라인에 `rehype-slug` 플러그인을 추가하여 각 heading에 자동으로 slug 기반 ID를 부여한다.

#### 파이프라인 변경

```
변경 전:
  remarkParse → remarkGfm → remarkRehype → rehypeShiki
  → rehypeExternalLinks → rehypeLazyImages → rehypeSanitize → rehypeStringify

변경 후:
  remarkParse → remarkGfm → remarkRehype → rehypeShiki
  → rehypeExternalLinks → rehypeLazyImages → rehypeSlug
  → rehypeSanitize → rehypeStringify
```

- `rehype-slug`: heading 텍스트를 slug화하여 `id` 속성 부여
- 예: `## 프로젝트 설정` → `<h2 id="프로젝트-설정">프로젝트 설정</h2>`
- `rehypeSanitize` 설정에 heading의 `id` 속성을 허용 목록에 추가

#### URL anchor 지원

- TOC 항목 클릭: `#프로젝트-설정` anchor로 스크롤
- 직접 URL 접근: `/posts/my-post#프로젝트-설정` → 해당 섹션으로 자동 스크롤
- 브라우저 기본 anchor 동작 활용

### 5.5 heading 추출

서버에서 마크다운 렌더링 시 heading 목록을 추출하여 페이지 컴포넌트에 전달한다.

```typescript
interface TocItem {
  id: string;       // slug 기반 anchor ID
  text: string;     // heading 텍스트
  level: 1 | 2 | 3; // h1, h2, h3
}
```

#### 추출 방법

마크다운을 HTML로 변환하기 전, MDAST(Markdown AST) 단계에서 heading 노드를 수집한다.

```typescript
// shared/lib/markdown.ts에 추가
export function extractHeadings(markdown: string): TocItem[] {
  const tree = unified().use(remarkParse).use(remarkGfm).parse(markdown);

  const headings: TocItem[] = [];
  visit(tree, 'heading', (node) => {
    if (node.depth >= 1 && node.depth <= 3) {
      const text = toString(node);        // mdast-util-to-string
      const id = slugify(text);           // rehype-slug와 동일한 slug 로직
      headings.push({ id, text, level: node.depth });
    }
  });

  return headings;
}
```

- `unist-util-visit`로 AST 순회
- `mdast-util-to-string`으로 heading 텍스트 추출
- `github-slugger` (rehype-slug 내부 사용)와 동일한 slugify로 ID 일치 보장

### 5.6 스크롤 동작

TOC 항목 클릭 시:

```tsx
<a
  href={`#${item.id}`}
  onClick={(e) => {
    e.preventDefault();
    const el = document.getElementById(item.id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      history.replaceState(null, '', `#${item.id}`);
    }
  }}
>
  {item.text}
</a>
```

- `scrollIntoView` smooth 스크롤
- URL hash 업데이트 (`replaceState`로 히스토리 오염 방지)
- 모바일에서 TOC 항목 클릭 시 TOC 접기 (사이드바가 슬라이드-인이므로 닫힘 처리)

### 5.7 컴포넌트 구조 (FSD)

| 계층 | 파일 | 역할 |
|---|---|---|
| `features` | `toc/ui/toc-section.tsx` | TOC 섹션 (접기/펼치기, 항목 렌더링) |
| `shared` | `lib/markdown.ts` | `extractHeadings` 함수 추가 |
| `widgets` | `PublicSidebar` | 글 상세일 때 TOC 섹션 조건부 렌더링 |

### 5.8 데이터 흐름

```
PostDetailPage (Server Component)
  ├─ fetchPost(slug) → post.contentMd
  ├─ extractHeadings(post.contentMd) → TocItem[]
  ├─ renderMarkdown(post.contentMd) → HTML (heading에 id 속성 포함)
  │
  └─ PublicSidebar에 headings 전달
     └─ TocSection (headings가 비어있으면 렌더링 안 함)

TocSection (Client Component)
  ├─ 데스크톱: 기본 펼침
  ├─ 모바일: 기본 접힘
  ├─ 항목 클릭 → smooth scroll + hash 업데이트
  └─ 접기/펼치기 토글
```

## 6. API 연동

서버 API 변경 없음. heading 추출은 클라이언트 서버 컴포넌트에서 마크다운 텍스트를 직접 파싱한다.

### 클라이언트 변경 사항

| 항목 | 설명 |
|---|---|
| `package.json` | `rehype-slug` 패키지 추가 |
| `shared/lib/markdown.ts` | 파이프라인에 `rehypeSlug` 추가, `extractHeadings` 함수 추가 |
| `shared/lib/markdown.ts` | `sanitizeSchema`에 heading `id` 속성 허용 추가 |
| `features/toc/ui/toc-section.tsx` | TOC 섹션 신규 |
| `widgets/PublicSidebar` | 글 상세 조건부 TOC 렌더링 |
| `app/posts/[slug]/page.tsx` | heading 추출 + 사이드바에 전달 |

## 7. 수용 기준

- [ ] 글 상세 페이지 사이드바 최상단에 TOC가 표시된다
- [ ] h1/h2/h3 heading이 계층적 들여쓰기로 표시된다
- [ ] heading이 없는 글에서는 TOC가 표시되지 않는다
- [ ] 다른 페이지(홈, 카테고리 등)에서는 TOC가 표시되지 않는다
- [ ] heading에 slug 기반 anchor ID가 부여된다
- [ ] TOC 항목 클릭 시 해당 섹션으로 smooth 스크롤된다
- [ ] URL `#anchor` 직접 접근 시 해당 섹션으로 이동한다
- [ ] 데스크톱에서 기본 펼침, 접기/펼치기 토글 동작
- [ ] 모바일에서 기본 접힘, 펼치기 가능
- [ ] 모바일에서 TOC 항목 클릭 시 TOC가 접힌다
- [ ] 다크모드 자동 적용
- [ ] 접근성: TOC `nav` 요소, `aria-label="목차"` (A-01 참조)
- [ ] Storybook story 작성 (F-38 참조)

## 8. 에지 케이스

| 케이스 | 처리 |
|---|---|
| heading 0개인 글 | TOC 섹션 미표시 |
| heading 1개만 있는 글 | TOC 표시 (1개라도 표시) |
| 동일 텍스트 heading 중복 | `github-slugger`가 자동으로 suffix 추가 (`id-1`, `id-2`) |
| heading에 마크다운 인라인 포맷 (볼드, 코드 등) | `mdast-util-to-string`으로 plain text 추출 |
| 매우 긴 heading 텍스트 | `line-clamp-1`로 1줄 말줄임 |
| heading에 특수문자 포함 | slug 변환 시 정규화 처리 |
| `rehypeSanitize`가 id 속성 제거 | sanitizeSchema에 h1-h3의 `id` 속성 명시적 허용 |

## 9. 의존성

- F-02 글 상세 (배치 위치, 마크다운 파이프라인)
- F-39 Public 사이드바 (사이드바 레이아웃)

## 10. 미해결 사항

없음. 모든 사항 확정됨.
