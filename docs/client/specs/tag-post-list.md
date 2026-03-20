# F-05: 태그별 글 목록

**상태:** DRAFT
**최종 수정:** 2026-03-20

---

## 1. 개요

태그 slug 기반 글 목록 페이지. 선택한 태그가 연결된 글을 페이지네이션하여 표시한다. 카테고리와 달리 계층 구조 없이 flat하게 동작한다.

## 2. 배경 및 동기

현재 태그별 글 목록이 구현되어 있으나 다음 개선이 필요하다:

- Pagination 표시 조건이 다른 페이지와 불일치 (태그 페이지는 조건 없이 항상 렌더링, 카테고리/홈은 `totalPages > 1` 이중 체크)

## 3. 목표

- Pagination 사용 패턴을 통일한다 (조건 없이 컴포넌트에 위임)
- F-01, F-03과 동일한 레이아웃 패턴을 유지한다
- 기존 구현의 동작을 문서화한다

## 4. 비목표

- 태그 계층 구조
- 태그별 정렬 옵션
- 관련 태그 추천

---

## 5. 상세 설계

### 5.1 페이지 구조

```
┌─────────────────────────────────────┐
│ [사이드바]  │  태그 헤더              │
│ (F-39)     │  Tag Archive            │
│             │  #JavaScript            │
│             │  총 8개의 글             │
│             ├─────────────────────────┤
│             │  PostCard               │
│             │  PostCard               │
│             │  PostCard               │
│             ├─────────────────────────┤
│             │  Pagination             │
└─────────────┴─────────────────────────┘
```

### 5.2 태그 헤더

```
┌─────────────────────────────────────┐
│ Tag Archive                          │
│ #JavaScript                          │ ← h1 (# 접두사 포함)
│ 총 8개의 글이 이 태그와 연결되어       │
│ 있습니다.                             │
└─────────────────────────────────────┘
```

- 라벨: "Tag Archive" (`text-body-xs`, uppercase, `tracking-[0.24em]`, `text-text-4`)
- 제목: `#{tag.name}` (`text-heading-md`, `text-text-1`)
- 글 수: `meta.total` 기반 (`text-body-md`, `text-text-3`)
- 컨테이너: `rounded-[2rem]`, `border border-border-3`, `bg-background-2`, `p-8 md:p-10`

### 5.3 데이터 흐름

```
TagPostsPage (Server Component)
  ├─ fetchTags() → GET /api/tags (전체 태그 목록)
  ├─ fetchPosts({ tagSlug: slug, page }) → GET /api/posts?tagSlug=javascript&page=1
  │   (두 요청 Promise.all로 병렬 실행)
  │
  ├─ tags.find(t => t.slug === slug) → activeTag
  │   └─ 없으면 notFound()
  │
  ├─ 태그 헤더
  ├─ PostCard 목록
  └─ Pagination (basePath: /tags/{slug})
```

### 5.4 서버 필터링 로직

서버는 `tagSlug`를 받아 다음 순서로 처리한다:

```
1. tagSlug로 tag 테이블에서 tag.id 조회
   └─ 없으면 빈 결과 반환
2. post_tags 조인 테이블에서 tag.id와 연결된 postId 목록 조회
   └─ 없으면 빈 결과 반환
3. WHERE post.id IN (...postIds) AND status='published' AND visibility='public'
4. 페이지네이션 적용 (LIMIT/OFFSET)
```

### 5.5 Pagination 사용 패턴 통일

`Pagination` 컴포넌트 내부에 `if (totalPages <= 1) return null` 로직이 이미 있으므로, 사용하는 쪽에서 조건 분기할 필요가 없다.

**통일 패턴 (F-01, F-03, F-05 모두 동일):**

```tsx
<Pagination
  currentPage={meta.page}
  totalPages={meta.totalPages}
  basePath={basePath}
/>
```

조건 래핑(`{meta.totalPages > 1 && ...}`) 없이 항상 렌더링하고, 표시 여부는 컴포넌트에 위임한다. F-01, F-03에서도 이 패턴으로 통일한다.

### 5.6 컴포넌트 구조 (FSD)

| 계층 | 파일 | 역할 |
|---|---|---|
| `app` | `tags/[slug]/page.tsx` | 페이지 컴포넌트 (SSR) |
| `entities` | `tag/api.ts` | `fetchTags` |
| `entities` | `post/api.ts` | `fetchPosts` (기존 재사용) |
| `features` | `post-list/ui/post-card.tsx` | 글 카드 (F-01 공유) |
| `shared` | `ui/libs/pagination.tsx` | 페이지네이션 (F-01 공유) |

### 5.7 빈 상태

태그에 글이 없을 때:

```
아직 이 태그에 연결된 공개 글이 없습니다.
```

`rounded-[2rem]`, `border-dashed`, `border-border-3`, `bg-background-2`

## 6. API 연동

| 메서드 | 경로 | 용도 |
|---|---|---|
| GET | `/api/tags` | 전체 태그 목록 (slug 검증용) |
| GET | `/api/posts?tagSlug={slug}&page={n}` | 태그별 글 목록 |

서버 변경 없음. 기존 API 그대로 사용.

## 7. 수용 기준

- [ ] 태그 slug로 접속 시 해당 태그의 글 목록이 표시된다
- [ ] 태그 헤더에 `#{tagName}`과 글 수가 표시된다
- [ ] PostCard, Pagination이 F-01과 동일하게 동작한다
- [ ] Pagination이 조건 래핑 없이 컴포넌트에 표시 여부를 위임한다
- [ ] 존재하지 않는 태그 slug 접속 시 404가 표시된다
- [ ] 글이 없는 태그에서 빈 상태 메시지가 표시된다
- [ ] 다크모드 자동 적용
- [ ] 접근성: 시맨틱 마크업 (A-01 참조)
- [ ] Storybook story 작성 (F-38 참조)

## 8. 에지 케이스

| 케이스 | 처리 |
|---|---|
| 존재하지 않는 tag slug | `notFound()` 호출 → 404 |
| 페이지 번호 초과 | `notFound()` 호출 → 404 |
| 페이지 번호 음수/문자열 | `parsePage()`에서 `notFound()` |
| 태그에 글이 0개 | 빈 상태 메시지 표시, 서버가 빈 배열 반환 |
| 동일 태그가 여러 글에 연결 | 정상 동작 (post_tags 조인) |

## 9. 의존성

- F-01 홈 - 글 목록 (PostCard, Pagination 공유)
- F-04 태그 목록 (태그 데이터 구조 공유)

## 10. 미해결 사항

없음. 모든 사항 확정됨.
