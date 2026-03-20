# F-03: 카테고리별 글 목록

**상태:** DRAFT
**최종 수정:** 2026-03-20

---

## 1. 개요

카테고리 slug 기반 글 목록 페이지. 선택한 카테고리와 그 하위 카테고리의 글을 모두 표시한다. 계층 경로(breadcrumb)로 현재 카테고리 위치를 안내하고, 페이지네이션으로 목록을 탐색한다.

## 2. 배경 및 동기

현재 카테고리별 글 목록이 구현되어 있으나 다음 개선이 필요하다:

- 상위 카테고리 선택 시 하위 카테고리 글이 포함되지 않음 (서버에서 `category_id` 단일 필터)
- 카테고리 페이지 상단에 pill 스타일 `CategoryNav`가 있으나, F-39 사이드바 도입 후 중복
- 카테고리 계층 경로(breadcrumb) 없음
- 글 수 표시가 해당 카테고리 직속 글만 집계
- `findCategoryBySlug` 유틸 함수가 페이지 컴포넌트 내에 위치

## 3. 목표

- 상위 카테고리 선택 시 하위 카테고리의 글을 포함하여 표시한다
- 카테고리 계층 경로(breadcrumb)를 표시한다
- 글 수에 하위 카테고리 글을 합산한다
- `CategoryNav` pill 컴포넌트를 제거한다 (F-39 사이드바로 대체)
- `findCategoryBySlug`를 entity 레이어로 이동한다
- F-01과 공유 컴포넌트(PostCard, Pagination)를 재사용한다

## 4. 비목표

- 카테고리 페이지 내 하위 카테고리 칩/필터 UI
- 카테고리 내 정렬 옵션 (최신순 고정)
- 카테고리 설명 텍스트

---

## 5. 상세 설계

### 5.1 페이지 구조

```
┌─────────────────────────────────────┐
│ [사이드바]  │  카테고리 헤더          │
│ (F-39)     │  프로그래밍 > JavaScript │
│             │  JavaScript             │
│             │  총 12개의 글            │
│             ├─────────────────────────┤
│             │  PostCard               │
│             │  PostCard               │
│             │  PostCard               │
│             │  ...                    │
│             ├─────────────────────────┤
│             │  Pagination             │
└─────────────┴─────────────────────────┘
```

### 5.2 카테고리 헤더

```
┌─────────────────────────────────────┐
│ Category Archive                     │
│ 프로그래밍 > JavaScript               │ ← breadcrumb (상위 카테고리 클릭 가능)
│ JavaScript                           │ ← h1 제목
│ 총 12개의 글이 이 카테고리에           │ ← 하위 포함 합산 수
│ 등록되어 있습니다.                     │
└─────────────────────────────────────┘
```

#### Breadcrumb

- 최상위 카테고리: breadcrumb 미표시 (자기 자신만)
- 하위 카테고리: `상위 > 하위` 형태로 표시
- 각 상위 카테고리는 클릭 가능한 링크 (`/categories/{slug}`)
- 마지막 항목(현재 카테고리)은 링크 없이 텍스트만

```tsx
<nav aria-label="카테고리 경로" className="flex items-center gap-1 text-body-xs text-text-4">
  {ancestors.map((ancestor, i) => (
    <Fragment key={ancestor.id}>
      {i > 0 && <span aria-hidden="true">{'>'}</span>}
      <Link href={`/categories/${ancestor.slug}`} className="hover:text-text-2 transition-colors">
        {ancestor.name}
      </Link>
    </Fragment>
  ))}
  {ancestors.length > 0 && <span aria-hidden="true">{'>'}</span>}
  <span className="text-text-3">{activeCategory.name}</span>
</nav>
```

### 5.3 서버 변경: 하위 카테고리 포함 필터링

클라이언트는 기존처럼 `categoryId` 하나만 전달한다. 서버가 해당 카테고리의 하위 카테고리를 재귀 조회하여 필터링한다.

#### 서버 로직 변경

```
기존: WHERE category_id = :categoryId
변경: WHERE category_id IN (:categoryId, ...하위_카테고리_ids)
```

**서버 구현 흐름:**

```
1. categoryId 수신
2. 해당 카테고리의 하위 카테고리를 재귀 조회
   └─ DB에서 parent_id = categoryId인 카테고리 조회
   └─ 재귀적으로 하위 탐색
3. 자신 + 하위 전체 id 목록 생성
4. WHERE category_id IN (...ids) 로 글 조회
```

카테고리 트리 depth가 깊지 않으므로(2~3 depth 예상) 성능 영향 미미. 카테고리 수가 적으므로 전체 카테고리를 한 번에 조회 후 메모리에서 트리 탐색하는 것이 효율적이다.

#### 글 수 합산

헤더에 표시되는 "총 N개의 글"도 하위 포함 합산 수. API 응답의 `meta.total`이 이미 하위 포함된 결과이므로 별도 처리 불필요.

### 5.4 유틸 함수 위치 정리

`findCategoryBySlug`를 페이지 컴포넌트에서 entity 레이어로 이동한다.

| 변경 전 | 변경 후 |
|---|---|
| `app/categories/[slug]/page.tsx` 내부 함수 | `entities/category/lib.ts` export 함수 |

추가로 breadcrumb용 상위 카테고리 경로를 구하는 함수도 entity에 배치한다.

```typescript
// entities/category/lib.ts
export function findCategoryBySlug(categories: Category[], slug: string): Category | undefined;
export function getCategoryAncestors(categories: Category[], targetId: number): Category[];
```

### 5.5 CategoryNav 제거

F-39 사이드바 도입 후 카테고리 페이지 상단의 pill 스타일 `CategoryNav` 컴포넌트를 제거한다.

| 항목 | 처리 |
|---|---|
| `widgets/category-nav/` | F-39 사이드바 완성 후 삭제 |
| 카테고리 페이지에서 CategoryNav import | 삭제 |
| 홈 페이지 CategoryNav 참조 (있는 경우) | 삭제 |

### 5.6 데이터 흐름

```
CategoryPage (Server Component)
  ├─ fetchCategories() → GET /api/categories (트리 구조)
  ├─ findCategoryBySlug(categories, slug) → activeCategory
  ├─ getCategoryAncestors(categories, activeCategory.id) → breadcrumb 경로
  ├─ fetchPosts({ categoryId: activeCategory.id, page })
  │   └─ GET /api/posts?categoryId=5&page=1
  │   └─ 서버가 하위 카테고리 재귀 포함하여 필터링
  │
  ├─ 카테고리 헤더 (breadcrumb + 제목 + 글 수)
  ├─ PostCard 목록
  └─ Pagination (basePath: /categories/{slug})
```

### 5.7 컴포넌트 구조 (FSD)

| 계층 | 파일 | 역할 |
|---|---|---|
| `app` | `categories/[slug]/page.tsx` | 페이지 컴포넌트 (SSR) |
| `entities` | `category/lib.ts` | `findCategoryBySlug`, `getCategoryAncestors` |
| `entities` | `category/api.ts` | `fetchCategories` |
| `entities` | `post/api.ts` | `fetchPosts` (기존 재사용) |
| `features` | `post-list/ui/post-card.tsx` | 글 카드 (F-01 공유) |
| `shared` | `ui/libs/pagination.tsx` | 페이지네이션 (F-01 공유) |

### 5.8 공유 컴포넌트 (F-01과 동일)

| 컴포넌트 | 동작 |
|---|---|
| `PostCard` | 썸네일 + 카테고리 + 날짜 + 제목 + 요약 + 태그 |
| `Pagination` | basePath만 `/categories/{slug}`로 변경 |

### 5.9 빈 상태

카테고리에 글이 없을 때:

```
┌─────────────────────────────────────┐
│ 아직 이 카테고리에 등록된              │
│ 공개 글이 없습니다.                   │
└─────────────────────────────────────┘
```

`rounded-[2rem]`, `border-dashed`, `border-border-3`, `bg-background-2`

## 6. API 연동

| 메서드 | 경로 | 용도 | 변경 사항 |
|---|---|---|---|
| GET | `/api/categories` | 카테고리 트리 조회 | 없음 (기존) |
| GET | `/api/posts?categoryId={id}&page={n}` | 카테고리 글 목록 | 서버: 하위 카테고리 재귀 포함 필터링 |

### 서버 변경 필요사항

| 항목 | 설명 |
|---|---|
| `PostService.getPostList()` | `categoryId` 수신 시 하위 카테고리 id를 재귀 조회하여 `WHERE category_id IN (...)` 적용 |

## 7. 수용 기준

- [ ] 카테고리 slug로 접속 시 해당 카테고리의 글 목록이 표시된다
- [ ] 상위 카테고리 선택 시 하위 카테고리의 글이 포함된다
- [ ] 카테고리 헤더에 breadcrumb 계층 경로가 표시된다
- [ ] breadcrumb의 상위 카테고리가 클릭 가능한 링크이다
- [ ] 글 수가 하위 카테고리 포함 합산 수로 표시된다
- [ ] PostCard, Pagination이 F-01과 동일하게 동작한다
- [ ] 페이지네이션 basePath가 `/categories/{slug}`이다
- [ ] 존재하지 않거나 비공개 카테고리 접속 시 404가 표시된다
- [ ] 글이 없는 카테고리에서 빈 상태 메시지가 표시된다
- [ ] CategoryNav pill 컴포넌트가 제거되었다 (F-39 사이드바로 대체)
- [ ] `findCategoryBySlug`가 `entities/category/lib.ts`에 위치한다
- [ ] 다크모드 자동 적용
- [ ] 접근성: breadcrumb `aria-label`, 시맨틱 마크업 (A-01 참조)
- [ ] Storybook story 작성 (F-38 참조)

## 8. 에지 케이스

| 케이스 | 처리 |
|---|---|
| 존재하지 않는 slug | `notFound()` 호출 → 404 |
| 비공개 카테고리 (`isVisible: false`) | `notFound()` 호출 → 404 |
| 페이지 번호 초과 | `notFound()` 호출 → 404 |
| 페이지 번호 음수/문자열 | `parsePage()`에서 `notFound()` |
| 하위 카테고리가 없는 카테고리 | 자기 자신 글만 표시 (기존 동작과 동일) |
| 최상위 카테고리 (부모 없음) | breadcrumb 미표시 |
| 깊은 카테고리 계층 (3+ depth) | breadcrumb에 전체 경로 표시, 서버 재귀 조회 정상 동작 |

## 9. 의존성

- F-01 홈 - 글 목록 (PostCard, Pagination 공유)
- F-39 Public 사이드바 (CategoryNav 제거 시점 의존)
- 서버: `PostService.getPostList()` 하위 카테고리 재귀 필터링 추가

## 10. 미해결 사항

없음. 모든 사항 확정됨.
