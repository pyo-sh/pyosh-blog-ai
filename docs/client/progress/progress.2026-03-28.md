# Client Progress - 2026-03-28

## 완료된 작업

### #197 목차 (TOC) (PR #244 머지)

글 상세 페이지 사이드바 최상단에 TOC를 추가하고, 마크다운 heading anchor와 smooth scroll 동작을 연결한 뒤 자동 리뷰 경고 3건을 반영해 병합했다.

**주요 변경 사항:**

- `src/shared/lib/markdown.ts`
  - `rehype-slug`를 렌더링 파이프라인에 추가하고, sanitize schema에서 `h1`~`h3`의 `id` 속성을 허용
  - `extractHeadings()`와 `TocItem` 타입을 추가해 마크다운 본문에서 h1/h2/h3 heading 목록을 추출
  - 렌더링된 heading과 TOC가 동일한 anchor를 사용하도록 `HEADING_ID_PREFIX`를 추출/렌더 양쪽에서 공유
- `src/app/(public)/posts/[slug]/page.tsx`
  - 서버에서 `post.contentMd`를 파싱해 TOC 데이터를 추출하고, 페이지 내 JSON payload로 직렬화
- `src/features/toc/ui/toc-section.tsx`
  - 데스크톱 기본 펼침 / 모바일 기본 접힘, 접기·펼치기 토글, smooth scroll, 모바일 클릭 시 접힘 처리를 포함한 TOC 섹션 추가
  - hash 갱신 시 `window.history.state`를 보존해 Next.js App Router history metadata를 깨지 않도록 수정
- `src/widgets/public-sidebar/ui/public-sidebar.tsx`
  - 글 상세 페이지에서만 TOC를 사이드바 최상단에 조건부 렌더링
  - post 페이지의 TOC payload를 읽어 headings가 없을 때는 섹션을 숨김
- `stories/app/public-sidebar.stories.tsx`, `stories/features/toc-section.stories.tsx`
  - PublicSidebar TOC 상태와 TOC 섹션 단독 Storybook 프리뷰 추가
- `package.json`, `pnpm-lock.yaml`
  - `rehype-slug`, `github-slugger`, `mdast-util-to-string` 의존성 추가

**리뷰 수정 사항:**

- `rehype-sanitize`와 TOC 추출 경로가 서로 다른 heading ID를 만들지 않도록 공통 prefix 상수로 정렬
- TOC 클릭이 Next.js App Router의 `history.state`를 지우지 않도록 `replaceState` 호출을 수정

**검증:**

- `pnpm compile:types`
- `pnpm lint`
- `pnpm build`

**메모:**

- 전체 `pnpm lint`는 저장소 기존 warning인 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 항목 1건이 그대로 남아 있었고, 이번 이슈 범위 밖으로 유지했다.

### #194 인기 글 (7일/30일) (PR #243 머지)

공개 사이드바의 "최근글 / 인기글" 탭에 7일/30일 인기 글 전환 UI를 추가하고, 기존 독립 `/popular` 페이지는 호환 리다이렉트만 남긴 채 사이드바 전용 흐름으로 전환했다.

**주요 변경 사항:**

- `src/features/popular-posts/ui/popular-post-list.tsx`
  - 7일/30일 pill 토글, 상위 5개 인기 글 목록, 빈 상태/에러 상태, 실패한 기간 재시도 로직을 포함한 클라이언트 컴포넌트 추가
  - 첫 SSR 로드 실패를 "빈 결과"로 캐시하지 않도록 분리해 기본 7일 뷰에서 재시도 가능하게 수정
- `src/features/recent-popular-posts/ui/recent-popular-posts.tsx`
  - 기존 최근글/인기글 탭 셸을 유지하면서 인기글 탭 본문을 `PopularPostList`로 위임
- `src/entities/stat/api.ts`, `src/app/(public)/layout.tsx`
  - `/api/stats/popular` 쿼리 생성 로직과 client fetch helper를 추가하고, 공개 레이아웃의 초기 인기 글 프리패치를 7일 상위 5개 기준으로 축소
- `src/app/(public)/popular/page.tsx`
  - 독립 페이지 UI는 제거하고, 기존 북마크/검색 유입을 깨지 않도록 홈(`/`)으로 리다이렉트하는 호환 라우트만 유지
- `src/widgets/header/navigation.tsx`
  - 헤더의 `/popular` 네비게이션 링크 제거
- `stories/features/popular-post-list.stories.tsx`
  - 기본/빈 상태/초기 로드 실패/다크 모드 Storybook 프리뷰 추가

**리뷰 수정 사항:**

- `/popular` 삭제가 404 회귀를 만들지 않도록 경량 리다이렉트 라우트를 복원
- 초기 7일 fetch 실패를 빈 목록으로 취급하지 않도록 상태를 분리하고, 선택된 기간에서 직접 재시도할 수 있게 보완

**검증:**

- `pnpm exec tsc --noEmit`
- `pnpm exec eslint src --ext .ts,.tsx`
- `pnpm exec next build`

**메모:**

- `pnpm lint` 스크립트 자체는 이 환경에서 로컬 `.bin/tsc` shim 경로 문제로 바로 실행되지 않아 동등한 `pnpm exec` 명령으로 검증했다.
- `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 warning 1건은 기존 경고로 남아 있었고, 이번 이슈 범위 밖으로 두고 병합했다.

### #195 카테고리별 글 목록 (PR #240 머지)

카테고리 글 목록 페이지를 F-39 공개 사이드바 레이아웃에 맞춰 정리하고, breadcrumb 기반 헤더와 Storybook 프리뷰를 추가한 뒤 병합했다.

**주요 변경 사항:**

- `src/app/(public)/categories/[slug]/page.tsx`
  - 상단 `CategoryNav` pill 네비게이션을 제거하고 breadcrumb + 제목 + 글 수 헤더로 재구성
  - `Pagination`의 `basePath`를 `/categories/{slug}`로 유지하고 `ScrollToTop`을 연결
  - slug 미존재, 비공개 카테고리, 잘못된 페이지 번호를 `notFound()`로 처리
- `src/entities/category/lib.ts`, `src/entities/category/index.ts`
  - `findCategoryBySlug`, `getCategoryAncestors`를 entity 레이어 공용 유틸로 추출
- `src/widgets/category-nav/*`
  - 더 이상 사용하지 않는 category pill 위젯 제거
- `stories/app/category-posts.stories.tsx`
  - breadcrumb 유무, 빈 상태, 페이지네이션, 모바일/다크 모드까지 확인할 수 있는 Storybook 프리뷰 추가

**검증:**

- `pnpm compile:types`
- `pnpm lint`
- `pnpm build`

**메모:**

- 전체 `pnpm lint`는 저장소 기존 warning인 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 항목 1건이 그대로 남아 있었다.
- 이슈 명세에 있던 "하위 카테고리 포함 글 조회 / 합산 수"는 서버 `main`에 아직 반영되지 않아 GitHub issue 체크리스트에서 미완료로 남겨 두었다.

### #189 CodeMirror 기반 마크다운 에디터 안정화 (PR #237 머지)

관리자 글 작성/수정용 CodeMirror 마크다운 에디터를 머지했다. 자동 리뷰에서 드러난 제어형 입력 동기화, 접근성, 툴바 명령, 번들 크기 회귀를 여러 라운드에 걸쳐 정리한 뒤 병합했다.

**주요 변경 사항:**

- `src/features/post-editor/ui/markdown-editor.tsx`
  - CodeMirror 에디터를 제어형 `value`와 안전하게 동기화하고, 외부 sync transaction은 `onChange`와 undo history에서 제외
  - `id`, `labelId`, placeholder 관련 속성을 재구성 가능하도록 정리
  - 실제 editor surface에 `id`를 유지하고 `spellcheck="false"`를 적용
  - hidden `textarea`는 form serialization 용도로만 유지
- `src/features/post-editor/lib/markdown-commands.ts`
  - heading/quote/list 툴바 동작이 multi-line selection 전체에 적용되도록 수정
  - code block / horizontal rule / table 삽입 시 줄바꿈 정규화
  - bold/italic/bold+italic 조합에서 inline emphasis toggle이 기존 마커를 파괴하지 않도록 보완
- `src/features/post-editor/ui/post-form.tsx`
  - 본문 라벨과 editor naming/focus 연결을 CodeMirror 구조에 맞게 조정
- `package.json`, `pnpm-lock.yaml`
  - `@codemirror/language-data` 제거로 불필요한 fenced-code language bundle 축소

**리뷰 수정 사항:**

- controlled sync가 dirty 상태를 다시 켜는 문제, undo가 hydration/reset 이전 내용을 되살리는 문제 수정
- exported `MarkdownEditor` prop 계약(`id`, `name`, `placeholder`)과 label wiring 회귀 보완
- toolbar의 block prefix, code block, horizontal rule, table, nested emphasis edge case 수정
- `@codemirror/language-data` 제거로 editor route 번들 부담 완화

**검증:**

- `pnpm compile:types`
- `pnpm lint`
- `pnpm build`

**메모:**

- 전체 `pnpm lint`는 저장소 기존 warning인 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 항목 1건이 남아 있었지만, 이번 이슈 수정 범위 밖으로 두고 병합했다.
