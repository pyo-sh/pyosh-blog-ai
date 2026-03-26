# [F-11] 검색

> 헤더의 검색 버튼으로 검색어를 입력하고, `/search` 페이지에서 검색 결과를 글 목록 형태로 표시한다. 6개 검색 필터를 드롭다운으로 제공하며, 검색어 하이라이팅을 지원한다.

## SPEC 참조

- `docs/client/specs/search.md`

## 와이어프레임

- `docs/client/designs/public/search.html` - 검색 페이지 전체
- 공통 디자인 시스템: `docs/client/designs/DESIGN_SYSTEM.md`

## 상세 설계

### 5.1 헤더 검색 입력

#### 동작 흐름

```
[🔍 아이콘 버튼]
  → 클릭 → [검색 입력 Input] 으로 변환, 자동 포커스
    → Enter → /search?q={query}&filter={filter} 이동
    → Esc → 아이콘으로 복원
    → 외부 클릭 → 아이콘으로 복원
```

#### 반응형 크기

| 뷰포트 | Input 최소 너비 | Input 최대 너비 |
|---|---|---|
| 데스크톱 (md+) | 200px | 320px |
| 모바일 | 120px | 가용 공간 전체 |

- `min-w-[120px] md:min-w-[200px] max-w-[320px]`
- flex 기반으로 다른 헤더 요소에 방해되지 않도록 가변 너비
- 입력 필드 오른쪽에 검색 필터 드롭다운 (모바일에서는 검색 페이지에서만 표시)

#### 접근성

- 아이콘 버튼: `aria-label="검색"`
- Input: `role="searchbox"`, `aria-label="검색어 입력"`
- Esc 키 핸들링: `onKeyDown` 이벤트

### 5.2 검색 필터

#### 드롭다운 옵션

| 필터 값 | 표시 텍스트 | 검색 대상 | 방식 |
|---|---|---|---|
| `title_content` | 제목 + 내용 | `post.title`, `post.content_md` | FULLTEXT |
| `title` | 제목 | `post.title` | FULLTEXT |
| `content` | 내용 | `post.content_md` | FULLTEXT |
| `tag` | 태그 | `tag.name` | JOIN + LIKE |
| `category` | 카테고리 | `category.name` | JOIN + LIKE |
| `comment` | 댓글 | `comment.body` | JOIN + LIKE |

- 기본값: `title_content` (제목 + 내용)
- URL 파라미터: `/search?q={query}&filter={filter}&page={n}`
- 검색 페이지에서 필터 변경 시 page 초기화 (1페이지로)

#### 드롭다운 UI

```
┌─ 검색 페이지 ─────────────────────────────────┐
│                                                 │
│  [제목 + 내용 ▼]  [검색어 입력___________] [🔍] │
│                                                 │
│  "JavaScript" 검색 결과 (8건)                    │
│                                                 │
│  PostListItem (하이라이팅 적용)                   │
│  PostListItem                                    │
│  PostListItem                                    │
│  ...                                             │
│                                                 │
│  Pagination                                      │
└─────────────────────────────────────────────────┘
```

- 드롭다운: `rounded-[1rem]`, `border border-border-3`, `bg-background-1`
- 검색 페이지 상단에 필터 + 검색 입력을 함께 배치

### 5.3 검색 결과 표시

#### 리스트 형식

검색 결과를 메인 페이지(F-01)와 동일한 리스트 형식으로 표시한다. PostListItem 그리드가 아닌 세로 리스트.

#### 검색 헤더

```
"JavaScript" 검색 결과 (8건)
```

- 검색어: `text-primary-1`, `font-medium`
- 건수: `text-text-3`

#### 댓글 검색 결과

댓글 검색 시 결과는 해당 댓글이 달린 **글** 단위로 표시한다.

```
┌─ 검색 결과 (댓글 필터) ──────────────────────┐
│ 글 제목 A                                     │
│ 2026.03.15 · 카테고리 · 조회 123               │
│                                               │
│ 일치하는 댓글: "...JavaScript 관련 질문..."     │  ← 댓글 발췌
└───────────────────────────────────────────────┘
```

- 댓글 필터일 때만 일치하는 댓글 내용 발췌를 추가로 표시
- 같은 글에 여러 댓글이 매칭되어도 글은 1번만 표시 (DISTINCT)

### 5.4 검색어 하이라이팅

클라이언트에서 검색어를 정규식으로 찾아 `<mark>` 태그로 감쌈.

```tsx
function highlightText(text: string, query: string): React.ReactNode {
  if (!query.trim()) return text;

  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const regex = new RegExp(`(${escaped})`, 'gi');
  const parts = text.split(regex);

  return parts.map((part, i) =>
    regex.test(part)
      ? <mark key={i} className="bg-primary-1/20 text-text-1 rounded-sm">{part}</mark>
      : part
  );
}
```

- 하이라이팅 대상: 제목, 요약(excerpt)
- 하이라이팅 스타일: `bg-primary-1/20`, `text-text-1`, `rounded-sm`
- 댓글 검색 시 댓글 발췌에도 적용

### 5.5 서버 검색 엔진 변경

#### FULLTEXT + ngram 인덱스

```sql
-- post_tb에 FULLTEXT 인덱스 추가
ALTER TABLE post_tb
  ADD FULLTEXT INDEX ft_title (title) WITH PARSER ngram,
  ADD FULLTEXT INDEX ft_content (content_md) WITH PARSER ngram,
  ADD FULLTEXT INDEX ft_title_content (title, content_md) WITH PARSER ngram;
```

ngram 토큰 크기: 기본값 2 (`ngram_token_size=2`). 한국어 2글자 이상 검색어에 대응.

#### 검색 쿼리 분기

```typescript
// filter별 검색 조건 분기
switch (filter) {
  case 'title_content':
    // FULLTEXT: MATCH(title, content_md) AGAINST('keyword' IN BOOLEAN MODE)
    conditions.push(
      sql`MATCH(${postTable.title}, ${postTable.contentMd}) AGAINST(${query} IN BOOLEAN MODE)`
    );
    break;

  case 'title':
    conditions.push(
      sql`MATCH(${postTable.title}) AGAINST(${query} IN BOOLEAN MODE)`
    );
    break;

  case 'content':
    conditions.push(
      sql`MATCH(${postTable.contentMd}) AGAINST(${query} IN BOOLEAN MODE)`
    );
    break;

  case 'tag':
    // JOIN + LIKE: tag_tb.name LIKE '%keyword%'
    // post_tag_tb JOIN tag_tb WHERE tag.name LIKE '%keyword%'
    break;

  case 'category':
    // JOIN + LIKE: category_tb.name LIKE '%keyword%'
    break;

  case 'comment':
    // JOIN + LIKE: comment_tb.body LIKE '%keyword%'
    // WHERE comment.status = 'active'
    // DISTINCT post_id
    break;
}
```

#### 정렬

모든 필터에서 `published_at DESC` (발행일 최신순) 고정. FULLTEXT 관련성 점수는 사용하지 않는다.

#### 댓글 검색 응답

댓글 필터로 검색 시 일치하는 댓글 발췌를 포함한다.

```typescript
interface SearchResultItem extends PostListItem {
  matchedComment?: {
    body: string;      // 댓글 원문 (또는 발췌)
    authorName: string;
  };
}
```

- 비밀 댓글은 검색 대상에서 제외 (`is_secret = false`)
- 삭제된 댓글도 제외 (`status = 'active'`)

### 5.6 컴포넌트 구조 (FSD)

| 계층 | 파일 | 역할 |
|---|---|---|
| `app` | `search/page.tsx` | 검색 결과 페이지 (SSR) |
| `widgets` | `header/search-bar.tsx` | 헤더 검색 입력 (기존 개선) |
| `features` | `search/ui/search-filter.tsx` | 검색 필터 드롭다운 |
| `features` | `search/lib/highlight.tsx` | 검색어 하이라이팅 유틸 |
| `features` | `post-list/ui/post-list-item.tsx` | 글 리스트 항목 (F-01 공유) |
| `entities` | `post/api.ts` | `fetchPosts` (filter 파라미터 추가) |
| `shared` | `ui/libs/pagination.tsx` | 페이지네이션 (F-01 공유) |

### 5.7 데이터 흐름

```
헤더 SearchBar
  └─ 검색어 입력 + Enter
  └─ router.push("/search?q=keyword&filter=title_content")

SearchPage (Server Component)
  ├─ searchParams에서 q, filter, page 추출
  ├─ fetchPosts({ q, filter, page })
  │   → GET /api/posts?q=keyword&filter=title_content&page=1
  │   → 서버: filter에 따라 FULLTEXT 또는 JOIN+LIKE 분기
  │
  ├─ 검색 헤더: "{keyword}" 검색 결과 (N건)
  ├─ 검색 필터 드롭다운 (Client Component)
  ├─ 글 리스트 (하이라이팅 적용)
  └─ Pagination (queryParams에 q, filter 포함)
```

## API 연동

| 메서드 | 경로 | 용도 | 변경 사항 |
|---|---|---|---|
| GET | `/api/posts?q={query}&filter={filter}&page={n}` | 검색 | `filter` 파라미터 추가, FULLTEXT 전환 |

### 서버 변경 필요사항

| 항목 | 설명 |
|---|---|
| DB 마이그레이션 | `post_tb`에 FULLTEXT 인덱스 추가 (ngram 파서) |
| `PostListQuerySchema` | `filter` 파라미터 추가 (enum: 6개 옵션) |
| `PostService.getPostList()` | filter별 검색 조건 분기 (FULLTEXT / JOIN+LIKE) |
| `PostService.getPostList()` | 댓글 필터 시 `matchedComment` 포함 |

### 응답 데이터

기존 `PostListResponse`를 확장한다.

```typescript
interface PostListItem {
  // ...기존 필드
  matchedComment?: {           // 댓글 필터일 때만 포함
    body: string;
    authorName: string;
  };
}
```

## 수용 기준

- [ ] 헤더 검색 아이콘 클릭 시 Input으로 전환, 자동 포커스
- [ ] Esc 키 또는 외부 클릭 시 아이콘으로 복원
- [ ] 검색 Input이 반응형 가변 너비를 가진다 (최소 120px/200px)
- [ ] Enter 시 `/search?q={query}&filter={filter}` 이동
- [ ] 6개 검색 필터 드롭다운이 동작한다
- [ ] 기본 필터가 "제목 + 내용"이다
- [ ] 제목/내용/제목+내용 검색이 FULLTEXT + ngram으로 동작한다
- [ ] 태그/카테고리 검색이 JOIN + LIKE로 동작한다
- [ ] 댓글 검색이 JOIN + LIKE로 동작하고, 일치 댓글 발췌가 표시된다
- [ ] 비밀/삭제된 댓글은 검색 대상에서 제외된다
- [ ] 검색 결과가 메인 페이지와 동일한 리스트 형식이다
- [ ] 검색어가 제목/요약에서 하이라이팅된다
- [ ] 검색 결과가 발행일 최신순으로 정렬된다
- [ ] 검색 결과 페이지네이션이 동작한다
- [ ] 빈 검색어 시 "검색어를 입력해 주세요" 표시
- [ ] 결과 없을 시 "검색 결과가 없습니다" 표시
- [ ] 다크모드 자동 적용
- [ ] 접근성: searchbox role, aria-label (A-01 참조)
- [ ] Storybook story 작성 (F-38 참조)

## 에지 케이스

| 케이스 | 처리 |
|---|---|
| 빈 검색어 | "검색어를 입력해 주세요" 안내 |
| 검색어 200자 초과 | 서버 Zod 검증 실패, 클라이언트 `maxLength` 제한 |
| 검색어 1자 | FULLTEXT ngram(2글자 토큰)에서 결과 없을 수 있음, 정상 동작 |
| SQL 특수문자 포함 | 서버에서 이스케이프 처리 |
| 결과 없음 | "검색 결과가 없습니다" 빈 상태 |
| 댓글 검색 시 같은 글에 여러 댓글 매칭 | 글 1번만 표시 (DISTINCT), 첫 번째 일치 댓글 발췌 |
| FULLTEXT 인덱스 미구축 상태 | 마이그레이션 필수 (배포 전 실행) |

## 의존성

- Blocked by: F-01
- Blocks: 없음
