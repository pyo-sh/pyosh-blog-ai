# Client Progress - 2026-03-27

## 완료된 작업

### #167 [F-01] 홈 - 글 목록 (PR #211 머지)

홈 페이지 글 목록 기능을 구현했다. 기존 카드형 `PostCard` 레이아웃을 리스트형으로 교체하고, 고정 글·페이지네이션 업그레이드·TanStack Query SSR 패턴을 적용했다.

**주요 변경 사항:**

- `entities/post/model.ts` — `Post` 타입에 `summary`, `isPinned`, `totalPageviews`, `commentCount`, `contentModifiedAt` 필드 추가
- `shared/ui/libs/pagination.tsx` — `[<<-5] [<-1] 번호 [+1>] [+5>>]` 형태, ±3 윈도우 + 생략(...) 패턴으로 업그레이드; 현재 페이지 버튼 `tabIndex={-1}` 적용
- `features/post-list/ui/post-list-item.tsx` — 새 리스트 아이템 컴포넌트: 썸네일(md+), 카테고리 배지, 발행일+수정일, 제목, 요약, 조회수·댓글수 표시; 핀 아이콘(`role="img"`)
- `features/post-list/ui/post-list-item-skeleton.tsx` — 페이지 전환 스켈레톤 로더
- `features/post-list/ui/post-list.tsx` — 클라이언트 컴포넌트: `useQuery` + SSR `initialData` + `Suspense` 래핑; `staleTime: 30_000`으로 중복 refetch 방지; `basePath` prop으로 재사용성 확보; 쿼리 키에 `basePath` 포함으로 캐시 충돌 방지
- `widgets/home-page/ui/home-page.tsx` — SSR 데이터 페칭 후 `initialData`를 `PostList`에 전달

**데이터 흐름:**
```
Server Component (SSR) → fetchPosts({ page }) → initialData
  └─ PostList (Client) → useQuery({ queryKey: ["posts", basePath, page], initialData, staleTime: 30_000 })
       └─ 페이지 변경 시 URL ?page=N 업데이트 → queryKey 변경 → refetch → 스켈레톤 표시
```

**에지 케이스 처리:**
- 글 없음: 빈 상태 메시지
- 로딩: 스켈레톤 10개
- 오류: 오류 메시지 섹션
- 범위 초과 페이지: SSR에서 404
- 고정 글만 있을 때: 페이지네이션 미표시

**리뷰 라운드:** 3회 (Warning 2건 수정, Suggestion 6건 수정)

### #168 [F-04] 태그 목록 (PR #212 머지)

태그 목록 기능을 구현했다. `/tags` 및 `/tags/[slug]` 페이지는 이전 PR에서 이미 구현되어 있었으며, 이번 PR에서는 `PostListItem` 태그 배지와 `TagCloud` feature 컴포넌트를 추가했다.

**주요 변경 사항:**

- `features/post-list/ui/post-list-item.tsx` — stats 행 아래에 텍스트 전용 태그 배지 추가; `rounded-full border border-border-3 px-3 py-1 text-body-xs`; 링크 없음
- `features/tag-cloud/ui/tag-cloud.tsx` — 새 `TagCloud` 컴포넌트: 상위 20개 태그를 `/tags/{slug}` 링크 배지로 표시, 하단 "태그 전체보기" 링크(`/tags`); F-39 사이드바 위젯에서 소비 예정
- `features/tag-cloud/index.ts` — barrel export

**스코프 참고:**

사이드바 통합(AC 2건)은 F-39 이슈 #185에서 처리. PR은 `Closes` 대신 `Refs #168`로 변경하여 이슈가 F-39 완료 시까지 열린 상태를 유지.

**리뷰 라운드:** 2회 (Critical 1건 - PR body Closes→Refs 수정)
