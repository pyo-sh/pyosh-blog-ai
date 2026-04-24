# Client Progress - 2026-04-24

## 완료된 작업

### #319 헤더에 방명록 네비게이션 링크 추가 (PR #321 머지)

공개 헤더에 이미 존재하던 `/guestbook` 페이지로 들어갈 수 있는 진입점이 없어 직접 URL 입력 외에는 접근하기 어려웠다. 이번 작업에서는 `src/widgets/header/index.tsx`의 우측 액션 그룹에 방명록 링크를 추가해 검색 아이콘 왼쪽에서 바로 `/guestbook`으로 이동할 수 있게 했다. 별도의 전역 네비게이션을 다시 도입하지 않고 기존 헤더 액션과 동일한 높이와 hover 패턴을 따르는 단일 링크로 정리해 데스크톱과 모바일 모두에서 현재 정렬을 유지했다. PR `#321`은 동기 `codex` 리뷰에서 clean 판정을 받은 뒤 병합됐다.

**주요 변경 사항:**

- `src/widgets/header/index.tsx`
  - `SearchBar` 앞에 `/guestbook` 링크 추가
  - 기존 헤더 컨트롤과 같은 `h-9` 높이, 간격, hover 색상 패턴 적용
  - 공개 헤더에서 모바일/데스크톱 공통으로 방명록 진입 경로 제공

**검증:**

- `pnpm compile:types`
- `pnpm lint` *(저장소 기존 warning 2건 유지)*
- `pnpm build`

**메모:**

- `pnpm lint` warning 2건은 기존 저장소 상태로, `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용과 `src/shared/ui/error-boundary.tsx`의 미사용 인자다.
- 헤더 링크는 별도 메뉴 컴포넌트를 재도입하지 않고 현재 액션 영역 안에서 최소 변경으로 노출했다.

### #318 카테고리 아카이브 페이지 `/categories` 추가 및 사이드바 전체보기 링크 정상화 (PR #320 머지)

공개 레이아웃의 사이드바 `CategoryTree`가 존재하지 않는 `/categories` 경로를 prefetch하면서 홈과 글 상세 등 모든 public 페이지에서 404 로그가 누적되던 문제를 정리했다. 이번 작업에서는 `src/app/(public)/categories/page.tsx`를 추가해 실제 아카이브 라우트를 만들고, 이미 존재하는 `/tags` 아카이브 셸 패턴을 따라 카테고리 전체보기를 노출하도록 맞췄다. 페이지 본문은 기존 `CategoryTree`를 그대로 재사용하되 `showOverviewLink={false}`를 적용해 아카이브 페이지 내부에서 자기 자신을 다시 링크하지 않도록 처리했다. 헤더에는 visible category 개수와 전체 published post 합계를 함께 표시해 카테고리 아카이브라는 의미를 분명히 했다. PR `#320`은 동기 `codex` 리뷰에서 추가 수정 없이 clean 판정을 받고 병합됐다.

**주요 변경 사항:**

- `src/app/(public)/categories/page.tsx`
  - `/categories` 공개 아카이브 라우트 신규 추가
  - `fetchCategories()`로 전체 카테고리 트리 조회
  - visible category node 개수와 `countVisibleCategories()` 기반 공개 글 합계 노출
  - 기존 `CategoryTree` 재사용, `showOverviewLink={false}` 적용
  - canonical metadata, empty state, `ScrollToTop` 포함

**검증:**

- `pnpm compile:types`
- `pnpm lint` *(저장소 기존 warning 2건 유지)*
- `pnpm build`

**메모:**

- `pnpm lint` warning 2건은 기존 저장소 상태로, `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용과 `src/shared/ui/error-boundary.tsx`의 미사용 인자다.
