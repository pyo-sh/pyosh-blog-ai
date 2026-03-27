# Client Progress - 2026-03-27

## 완료된 작업

### #187 관리자 대시보드 - 통계/글 상태/최근 댓글 (PR #233 머지)

단일 252줄 `dashboard-home.tsx`를 3개의 집중된 서브 위젯으로 분리했다. 각 위젯은 독립적으로 로딩/에러/빈 상태를 처리하고, TanStack Query `["dashboard", "stats"]` 공유 키로 네트워크 요청을 중복 제거한다.

**주요 변경 사항:**

- `src/entities/stat/model.ts` - `DashboardStats`에 `postsByStatus: { draft, published, archived }` 필드 추가
- `src/shared/lib/format-number.ts` (신규) - `Intl.NumberFormat('ko-KR')` 싱글톤을 공유 유틸로 추출 (`formatNumber(value: number): string`)
- `src/widgets/dashboard/ui/stats-section.tsx` (신규) - 오늘/7일/30일 페이지뷰 통계 카드 3개. `["dashboard", "stats"]` 쿼리 키 사용. `formatNumber` 직접 호출 (중간 wrapper 없음)
- `src/widgets/dashboard/ui/post-status-section.tsx` (신규) - 전체/발행/임시저장/보관 글 수 카드 4개. 전체 카드는 수동 합산 대신 `data.totalPosts` 사용 (서버 추가 상태 대응). 각 카드는 `/manage/posts?status=...` 링크
- `src/widgets/dashboard/ui/recent-comments-section.tsx` (신규) - 최신 댓글 목록 (페이지당 5개), 인라인 삭제. `deleteError` 인라인 표시, `onMutate`에서 초기화 (재시도 시 stale 오류 메시지 제거). SecretIcon `<svg>`에 `role="img"` 추가 (aria-label 스크린리더 호환)
- `src/widgets/dashboard/ui/dashboard-home.tsx` - 3개 서브 위젯 조합으로 교체

**리뷰 라운드:** 4회
- Round 1 ([WARNING] 1, [SUGGESTION] 2): delete 오류 무음 처리 - `deleteError` 인라인 상태 추가; SecretIcon `role="img"` 누락; `STAT_CARDS.label` 미사용 필드 제거
- Round 2 ([WARNING] 1): 전체 글 수 수동 합산 - `data.totalPosts` 사용으로 교체
- Round 3 ([WARNING] 1, [SUGGESTION] 1): `deleteError` 재시도 시 stale 표시 - `onMutate` 클리어 추가; `numberFormatter` 중복 - `@shared/lib/format-number` 추출
- Round 4 ([SUGGESTION] 2): 불필요한 `formatStatValue` wrapper 제거; `toLocaleString` 직접 호출을 `formatNumber`로 교체 - skipReview로 merge

---

### #185 [F-39] Public 사이드바 레이아웃 (PR #232 머지)

모든 Public 페이지에 2컬럼 레이아웃(사이드바 + 본문)을 적용했다. 데스크톱에서는 스마트-스티키 사이드바, 모바일에서는 햄버거 버튼 + 슬라이드-인 패널로 동작한다.

**주요 변경 사항:**

- `src/entities/stat/model.ts` - `TotalViewsStats` 인터페이스 추가
- `src/entities/stat/api.ts` - `fetchTotalViews()` 추가
- `src/entities/category/model.ts` - `publishedPostCount?`, `totalPostCount?` 필드 추가
- `src/app-layer/style/animation.css` - `slide-in-right` 키프레임 + `--animate-slide-in-right` CSS 변수 추가
- `src/shared/ui/libs/slide-in-panel.tsx` (신규) - 포커스 트랩, ESC 닫기, `role="dialog" aria-modal` 슬라이드-인 패널
- `src/features/category-tree/ui/category-tree.tsx` (신규) - 재귀 카테고리 트리, `aria-expanded` 토글, depth 기반 들여쓰기
- `src/features/recent-popular-posts/ui/recent-popular-posts.tsx` (신규) - 최신/인기 탭 전환, `role="tablist"`, `aria-selected`
- `src/features/total-view-count/ui/total-view-count.tsx` (신규) - 총 조회수 표시 (`toLocaleString("ko-KR")`)
- `src/widgets/public-sidebar/ui/public-sidebar.tsx` (신규)
  - `PublicSidebarContent` - 사이드바 4개 섹션 렌더링
  - `StickySidebarWrapper` - JS 스크롤 연동 sticky (사이드바 높이 > 뷰포트일 때 콘텐츠 따라 스크롤), `NAV_HEIGHT = 72`, `lastScrollY` = `window.scrollY`로 초기화
- `src/widgets/header/index.tsx` - 내비게이션 제거, 햄버거 버튼 추가 (`lg:` 이상에서 숨김), `hamburgerRef` prop 추가
- `src/app/(public)/layout-shell.tsx` (신규) - Client Component, 2컬럼 레이아웃, `PublicLayoutShell`, 리사이즈 시 자동 닫기(1080px), 닫힌 후 햄버거 버튼으로 포커스 반환
- `src/app/(public)/layout.tsx` - async Server Component로 전환, `Promise.all`로 사이드바 데이터 SSR 페치, 모든 fetch에 `.catch()` graceful degradation
- `stories/app/public-sidebar.stories.tsx` (신규) - Storybook story (Default/NoCategories/NoTags/Empty/DarkMode)

**리뷰 라운드:** 2회
- Round 1 ([WARNING] 1개, [SUGGESTION] 3개): `closeBtnRef` - 언마운트된 버튼 대신 햄버거 버튼으로 포커스 반환(findings-012), `NAV_HEIGHT` 70→72 수정, `fetchPosts/Categories/Tags`에 `.catch()` 추가
- Round 2 ([SUGGESTION] 3개): `lastScrollY` 초기화 버그 수정(0→window.scrollY), 나머지 2개(포커스 트랩 재쿼리, 상수 추출)는 skip

---

### #181 [F-11] 검색 - 필터/하이라이팅/댓글 발췌 (PR #231 머지)

헤더 검색 바 UX 개선, 6개 필터 드롭다운, 검색어 하이라이팅, 댓글 검색 발췌 표시를 구현했다.

**주요 변경 사항:**

- `src/entities/post/model.ts`
  - `SearchFilter` 타입 추가 (6개 값: title_content, title, content, tag, category, comment)
  - `SEARCH_FILTERS` const 추가 - 페이지 validation과 타입을 단일 소스로 통일
  - `MatchedComment` 인터페이스 추가 (`body`, `authorName`)
  - `Post`에 `matchedComment?` 필드 추가 (댓글 필터 시 서버가 포함)
  - `FetchPostsParams`에 `filter?` 필드 추가
- `src/entities/post/api.ts` - `filter` 파라미터를 query string에 추가
- `src/features/search/lib/highlight.tsx` - `highlightText()` 유틸 (split 홀수 인덱스 기반 `<mark>` 래핑)
- `src/features/search/ui/search-filter.tsx` - `SearchFilterDropdown` 컴포넌트 (6개 옵션 `<select>`, 필터 변경 시 URL 업데이트)
- `src/features/search/ui/search-result-item.tsx` - 하이라이팅 + 댓글 발췌가 포함된 리스트 아이템
- `src/features/search/index.ts` - barrel export
- `src/widgets/header/search-bar.tsx`
  - Esc 키 닫기, 외부 클릭 닫기 추가
  - `role="searchbox"` 제거 (input[type=search] 암시적 role)
  - 반응형 크기: `min-w-[120px] md:min-w-[200px] max-w-[320px]`
  - `/search` 페이지에서 열 때 현재 filter 값 유지
- `src/app/(public)/search/page.tsx`
  - `PostCard` - `SearchResultItem`으로 교체 (리스트 형식)
  - `SearchFilterDropdown` 드롭다운 추가 (빈 상태 포함)
  - `filter` 파라미터 읽기/전달 + Pagination queryParams에 포함
  - 검색 헤더 형식 변경: `"keyword" 검색 결과 (N건)`

**리뷰 라운드:** 2회
- Round 1 (4개 제안): regex.test 대신 홀수 인덱스 검사 적용, SearchFilterDropdown으로 컴포넌트 이름 변경, authorName UI 렌더링 추가, role="searchbox" 제거
- Round 2 (2개 제안): next/image 허용 호스트 주석 추가, SEARCH_FILTERS const 추출로 중복 제거

---

### #174 [F-34c] CSP (Content Security Policy) (PR #225 머지)

Next.js middleware에서 nonce 기반 CSP 헤더를 설정했다. 초기 배포는 `Content-Security-Policy-Report-Only`(phase 1)로 차단 없이 위반 로그만 수집하며, `script-src`에 `strict-dynamic`을 포함해 Next.js 하이드레이션 스크립트를 준비했다.

**주요 변경 사항:**

- `src/middleware.ts`
  - `buildCspDirectives(nonce)` 헬퍼 - dev/prod 분기 (`img-src`에 dev만 `http:` 허용), `script-src 'nonce-{random}' 'strict-dynamic'`, `object-src 'none'`, `connect-src 'self' ${NEXT_PUBLIC_API_URL}` (apiUrl 미설정 시 조건부 생략), `style-src 'self' 'unsafe-inline'` (phase 2 전환 전 교체 필요, 코드 주석 명시)
  - `nextWithCsp(request, nonce)` 헬퍼 - request headers에 `x-nonce` 설정 (App Router가 자동 적용), response headers에 `Content-Security-Policy-Report-Only` 설정
  - nonce 생성: `Buffer.from(crypto.randomUUID()).toString("base64")`
  - matcher 확장: `/manage/:path*` + `/((?!_next/static|_next/image|...)$).*)` 전체 페이지 라우트 커버
  - `/manage` 경로 가드 조건 정밀화: `startsWith(MANAGE_HOME_PATH)` → `=== MANAGE_HOME_PATH || startsWith(\`${MANAGE_HOME_PATH}/\`)`

**리뷰 라운드:** 5회 (round limit 도달, 사용자 결정으로 merge)
- Round 1: `connect-src` apiUrl 미설정 시 trailing whitespace 조건부 생략으로 수정
- Round 2: `'strict-dynamic'` 추가, `/manage` 경로 가드 정밀화
- Round 3: `object-src 'none'` 추가
- Round 4: `unsafe-inline` phase 2 prerequisite 주석 추가
- Round 5: report endpoint (API 연동: 없음으로 out of scope) - merge

**Phase 2 전환 전 필수 항목:**
- `style-src 'unsafe-inline'` → nonce 기반 스타일로 교체
- `report-uri /api/csp-report` 엔드포인트 구현 및 디렉티브 추가
- `Content-Security-Policy-Report-Only` → `Content-Security-Policy` 전환

---

### #180 [F-38] Storybook 환경 구성 (PR #226 머지)

Storybook 10 + MSW 2 + TanStack Query 기반 컴포넌트 개발·검토 환경을 구성했다. DB/서버 없이 모든 화면을 Storybook에서 확인할 수 있다.

**주요 변경 사항:**

- `.storybook/main.ts` - `@storybook/nextjs` 프레임워크, webpack alias 설정(`@app`, `@widgets` 등 FSD 경로), `@storybook/addon-themes`·`@storybook/addon-a11y` 애드온
- `.storybook/preview.tsx` - `useState` factory 패턴으로 QueryClient 스토리당 격리, `onUnhandledRequest: "bypass"` MSW 초기화, 다크/라이트 모드 데코레이터, 모바일(375px)/데스크톱(1280px) 뷰포트
- `tsconfig.storybook.json` - `moduleResolution: bundler`로 Storybook v10 패키지 타입 호환
- `package.json` - `"storybook": "storybook dev -p 6006"` 스크립트 추가 (로컬 전용, build-storybook 미포함)
- `public/mockServiceWorker.js` - MSW 서비스 워커 (`pnpm exec msw init public/`)
- `stories/mocks/handlers.ts` - 공통 API 핸들러 (posts, categories, comments, guestbook, assets, stats, auth 7개 도메인)
- `stories/mocks/data/` - 6개 도메인 목 데이터 (SVG data URL 기반 placeholder 이미지, 도메인별 정확한 pagination meta)
- 스토리 파일 22개 - FSD 계층(App, Widgets/Admin, Features, Shared) 구조로 배치; Default/Empty/Error/DarkMode/Mobile 변형 포함

**Storybook v10 주요 이슈 (findings.011 참조):**

- `@storybook/addon-essentials`는 v10 코어에 통합 - 별도 설치 불필요
- `moduleResolution: node`로는 v10 패키지 타입 해석 불가 - 전용 `tsconfig.storybook.json` 필요
- `QueryClient` 싱글톤/직접 생성은 스토리 간 캐시 오염 - `useState` factory 패턴으로 해결

**리뷰 라운드:** 3회
- Round 1: Warning 2건 - QueryClient 싱글톤 캐시 공유 문제, `stories/` tsconfig 미포함
- Round 2: Warning 2건 - QueryClient 직접 생성(re-render 시 캐시 초기화), `via.placeholder.com` 외부 URL 의존
- Round 3: Suggestion 3건 - mockMeta 총계 불일치, PostList 스토리 제목 오해 소지 (적용), build-storybook 누락 (스펙상 제외)

---

### #169 [F-13] 로딩/빈 상태 (PR #217 머지)

`Skeleton`, `Spinner`, `EmptyState` 공유 컴포넌트를 `@shared/ui/libs`에 추가하고, 기존 7개 로컬 스켈레톤 정의와 인라인 빈 상태 패턴을 교체했다.

**주요 변경 사항:**

- `shared/ui/libs/skeleton.tsx` - NEW: `variant`(text/circle/rect), `width`, `height`, `repeat`, `className` props. 각 variant별 기본 크기 및 `animate-pulse bg-background-3`. `aria-busy="true"` wrapper로 접근성 확보.
- `shared/ui/libs/spinner.tsx` - NEW: `size`(sm/md) prop. `aria-hidden="true"` SVG만 렌더링, `role="status"` 미포함 (버튼 내부 이중 공지 방지).
- `shared/ui/libs/empty-state.tsx` - NEW: `variant`("default" | "page"), `icon`, `message`, `className` props. `default` - 관리자 스타일(`bg-background-1 px-6 py-12 text-sm`), `page` - 공개 페이지 스타일(`bg-background-2 p-8 md:p-10 text-body-md`).
- `shared/ui/libs/index.tsx` - `EmptyState`, `Skeleton`, `Spinner` export 추가 (main 브랜치의 `ErrorContent`, `ScrollToTop`과 병합).
- 로컬 스켈레톤 7개 제거: `TableSkeleton`(posts, guestbook-manager), `TreeSkeleton`(category-manager), `DashboardLoading`/`DashboardStatsSkeleton`(dashboard), `PostListItemSkeleton`(post-list), `app/loading.tsx` 인라인.
- Spinner 적용: login-form, category-form-modal, category-manager, guestbook-form, guestbook-manager, comment-form, comment-list, post-form, asset-uploader, upload-zone의 제출/삭제 버튼.
- EmptyState(variant="page") 적용: tags, tags/[slug], search, categories/[slug], popular, post-list, guestbook-form.

**리뷰 라운드:** 4회
- Round 1: `role="status"` 이중 공지 제거, circle variant 기본 너비(`2rem`) 추가
- Round 2: EmptyState `className` prop 추가, category-form-modal typo 수정(`submitingLabel` → `submittingLabel`)
- Round 3: EmptyState `variant` prop 도입, 공개 페이지 전용 스타일 분리
- Round 4: `default` variant에 `text-sm` 누락 추가

**병합 충돌:** main 브랜치의 `ScrollToTop`/`ErrorContent` 도입, `getErrorMessage` 추출(#171/#172/#173)과 충돌. `git merge origin/main`으로 8개 파일 충돌 수동 해소.

---

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

### #170 [F-09] 방명록 (PR #213 머지)

방명록 페이지(F-09)를 구현했다. 게스트/OAuth 사용자 작성·삭제, 비밀글, flat 구조, 상대 시간 표시를 완성했다.

**주요 변경 사항:**

- `entities/guestbook/model.ts` - `BaseCreateGuestbookBody`에서 `parentId` 제거 (방명록 flat 구조 명시)
- `features/guestbook-form/ui/guestbook-page-content.tsx` - 여러 기능 완성:
  - `formatRelativeTime` - "3분 전", "1시간 전", "2일 전" 형태의 상대 시간 표시 (30일 초과 시 절대 날짜 폴백); 음수 diffMs 가드 추가
  - flat 구조 렌더링 - replies 재귀 제거, `appendGuestbookEntry`·`markGuestbookDeleted` 단순화
  - 작성 후 스크롤 이동 - `newEntryRef` + `scrollIntoView({ behavior: "smooth" })`
  - OAuth 배지 표시 - OAuth 사용자 항목에 배지 추가
  - 비밀글 body 마스킹 - `isSecret && !body` 조건으로 "비밀 방명록입니다." 표시
  - 헤더에 "총 N개 방명록" 카운트 표시

**데이터 흐름:**
```
GuestbookPage (Server Component, SSR)
  └─ fetchMeServer() → guest/oauth 구분
  └─ fetchGuestbook(page) → flat 목록
       └─ GuestbookPageContent (Client)
            ├─ CommentForm variant="guestbook" → POST /api/guestbook → 목록 prepend + scroll
            └─ Modal → DELETE /api/guestbook/:id → soft delete 마스킹
```

**미완료 DoD:**
- F-13 EmptyState 컴포넌트 (별도 이슈)
- F-38 Storybook story (별도 이슈)
- A-01 모달 포커스 트랩 (별도 이슈)

**리뷰 라운드:** 1회 (Suggestion 2건 수정 - 클락 스큐 가드, 중복 의존성 제거)

### #177 [F-17] 다크 모드 (PR #218 머지)

CSS 변수 기반 다크/라이트 테마 시스템을 완성했다. 핵심 인프라(theme.css, ThemeProvider, layout.tsx)는 이미 존재했으며, 미완성 항목 3가지를 완료했다.

**주요 변경 사항:**

- `app-layer/style/transition.css` - `.transition-theme`에 `border-color`·`box-shadow` 추가 (스펙 명시 변경사항)
- `widgets/header/theme-button.tsx` - 토글 버튼에 `aria-label` 추가 (`다크 모드로 전환` / `라이트 모드로 전환`)
- `shared/lib/cookie.ts` - `setCookie` 재작성: 이전 구현이 `document.cookie` setter 시맨틱을 오해하여 쿠키 전체 문자열을 덮어쓰려 했으나 브라우저는 단일 쿠키만 파싱함. 새 구현은 올바른 단일 할당으로 수정하고 `path=/; SameSite=Lax; Secure; Max-Age` 속성 추가
- `app-layer/theme/theme-provider.tsx` - 테마 쿠키에 `Max-Age=1년` 적용 (재방문 시 유지)

**리뷰 라운드:** 1회 (Suggestion 1건 - cookie.ts에 Secure 플래그 추가)

### #172 [F-15] 맨 위로 버튼 (PR #214 머지)

맨 위로 버튼(F-15)을 구현했다. 긴 콘텐츠 페이지에서 1 viewport 이상 스크롤 시 우하단에 페이드인되고, 클릭 시 smooth scroll로 상단으로 이동한다.

**주요 변경 사항:**

- `shared/ui/icons/arrow-up-icon.tsx` - 업 화살표 SVG 아이콘 컴포넌트
- `shared/ui/libs/scroll-to-top.tsx` - ScrollToTop 컴포넌트: `fixed bottom-6 right-6 z-40`, `hidden md:flex`(데스크톱 전용), throttle 100ms scroll handler, `handleScroll()` 마운트 즉시 호출로 초기 상태 동기화, `aria-label="맨 위로"`, opacity 페이드인/아웃
- 5개 페이지에 배치: `posts/[slug]`, `tags`, `tags/[slug]`, `search`, `guestbook`

**리뷰 라운드:** 2회 (Warning 1건 - 하드 리로드 시 초기 상태 미동기화 수정, Suggestion 1건 - PR description breakpoint 오기재 수정)

### #173 [F-12] 에러 페이지 (PR #215 머지)

에러 페이지 시스템(F-12)을 구현했다. `ErrorContent` 공통 컴포넌트를 도입하고, Public/Admin 에러 경계에 일관되게 적용했다.

**주요 변경 사항:**

- `shared/ui/libs/error-content.tsx` - NEW: badge(`primary` | `negative`), title, description, action(`link` | `button`)을 props로 받는 에러 카드 컴포넌트. h1 heading 계층 구조로 접근성 확보.
- `shared/ui/libs/index.tsx` - `ErrorContent` export 추가
- `app/not-found.tsx` - `ErrorContent` 사용으로 리팩터링 (Public 404, primary 배지, "홈으로 돌아가기" 링크)
- `app/error.tsx` - `ErrorContent` 사용으로 리팩터링 (Public 500, negative 배지, "다시 시도" 버튼)
- `app/global-error.tsx` - `ErrorContent` 사용으로 리팩터링 + `@app-layer/style/index.css` import 추가 (루트 레이아웃 밖 렌더링이므로 필요)
- `app/dashboard/not-found.tsx` - NEW: Admin 404, `dashboard/layout.tsx`가 사이드바를 유지하므로 `<div>` 래퍼만 사용, "관리 홈으로 돌아가기" 링크 (`/dashboard`)
- `app/dashboard/error.tsx` - NEW: Admin 500, 사이드바 유지, "다시 시도" 버튼
- `shared/api/client.ts` - `clientFetch`에 403 인터셉터 추가: `/dashboard` 경로에서만 `/dashboard/login?reason=forbidden`으로 리다이렉트 (공개 페이지 영향 없음)

**주요 결정:**

- `ErrorContent`의 최대 너비를 `max-w-[32rem]`으로 통일 (기존 Not Found는 `max-w-[36rem]` 사용) - 500/404 일관성 확보
- 403 인터셉터는 `window.location.pathname.startsWith("/dashboard")` 조건으로 공유 레이어에서 경로 분기 처리 - 공개 API 호출이 403을 받아도 대시보드 로그인으로 리다이렉트되지 않음
- `role="alert"`는 정적 에러 페이지에 부적합 - h1 heading 계층 구조로 대체

**리뷰 라운드:** 3회 (Round 1: Warning 1건 - window.alert 제거/리다이렉트로 교체, Suggestion 1건 - 중복 aria-live 제거. Round 2: Critical 1건 - 403 인터셉터 공유 레이어 경로 분기, Warning 1건 - role=alert 제거)

### #171 [F-14] Toast 알림 (PR #216 머지)

전역 Toast 알림 시스템(F-14)을 구현했다. `sonner`를 도입하고, 7개 파일에 분산된 `getErrorMessage` 유틸을 `@shared/lib`으로 추출했으며, 서버 요청 결과 피드백을 Toast로 전환했다.

**주요 변경 사항:**

- `shared/lib/get-error-message.ts` - NEW: `ApiResponseError` → `.message`, `Error && error.message` → `.message`, fallback 순서로 처리하는 공유 유틸. 기존 7개 파일의 중복 구현을 통합
- `app-layer/provider/toast-provider.tsx` - NEW: `<Toaster position="top-right" duration={3000} visibleToasts={3} closeButton />`; `useTheme()`으로 `themeType`을 읽어 sonner `theme` prop에 연결 (`"default"` → `"system"` 매핑)
- `app-layer/provider/index.tsx` - `ThemeProvider` 내부에 `<ToastProvider />` 추가
- 7개 파일 마이그레이션:
  - `features/post-editor/ui/post-form.tsx` - `onError: setSubmitError` → `toast.error`; 폼 검증 오류(카테고리·제목) 인라인 유지
  - `features/asset-uploader/ui/asset-uploader.tsx` - `feedbackMessage`·`errorMessage` 상태 완전 제거; 업로드/삭제 성공 → `toast.success`, 에러 → `toast.error`, 클립보드 복사 → `toast.info`; 파일 검증 오류도 `toast.error`로 전환
  - `features/comment-section/ui/comment-form.tsx` - catch block `setErrorMessage` → `toast.error`; "본문을 입력해 주세요" 인라인 유지
  - `features/category-manager/ui/category-manager.tsx` - `actionError` 상태 완전 제거; mutation `onError` → `toast.error`; "하위 카테고리가 있는 항목은 삭제할 수 없습니다" → `toast.error`
  - `features/category-manager/ui/category-form-modal.tsx` - dead `errorMessage` prop 제거
  - `features/admin-login/ui/login-form.tsx` - catch block `setErrorMessage` → `toast.error`; `errorMessage` 상태 완전 제거
  - `app/dashboard/posts/page.tsx` - `actionError` 상태 완전 제거; mutation `onError` → `toast.error`
  - `features/guestbook-manager/ui/guestbook-manager.tsx` - `actionError` 상태 완전 제거; mutation `onError` → `toast.error`

**주요 결정:**

- 폼 검증 오류(카테고리·제목·본문 empty)는 인라인 유지; 서버 요청 결과만 Toast로 전환
- `"default"` 테마는 sonner의 `"system"`으로 매핑하여 OS 다크 모드 자동 연동
- `CategoryFormModal.errorMessage` prop은 항상 null이 되어 dead interface가 되므로 prop 자체를 제거

**리뷰 라운드:** 2회 (Round 1: Warning 2건 - 잔여 inline 에러 상태 dead code 제거, Suggestion 1건 - `error.message` 빈 문자열 가드 추가. Round 2: Suggestion 1건 - CategoryFormModal dead errorMessage prop 제거)

---

### #175 [F-19] 관리자 로그인 (PR #219 머지)

관리자 인증 시스템을 구현했다. 아이디/비밀번호 기반 로그인, `/manage/*` 경로 인증 가드, 사이드바 로그아웃 버튼을 완성했다.

**주요 변경 사항:**

- `src/middleware.ts` - 경로 `/dashboard/*` → `/manage/*` 이전. matcher, 상수, `redirectToDashboard` → `redirectToManage` 함수명 업데이트
- `src/app/dashboard/` → `src/app/manage/` - 관리 페이지 라우팅 디렉터리 전체 이전 (15개 파일). 내부 하이퍼링크 `/dashboard/...` → `/manage/...` 일괄 변경
- `src/entities/auth/model.ts` - `LoginCredentials.email` → `username`, `CurrentAdminUser.email` → `username`, `AdminUser.email` → `username`
- `src/features/admin-login/ui/login-form.tsx` - 이메일 필드 → 아이디 필드 (`type="text"`, `autoComplete="username"`). 로그인 성공 후 `/manage`로 이동
- `src/widgets/admin-sidebar/ui/admin-sidebar.tsx` - 메뉴 경로 전체 `/manage/*`로 업데이트. 상단 로그아웃 버튼 추가 (`useTransition`, `logout()` 호출, 실패 시 Toast)
- `src/shared/api/client.ts` - 403 인터셉터 경로 조건 및 리다이렉트 대상 `/manage/login`으로 업데이트

**리뷰 라운드:** 1회 (Suggestion 1건 - `DashboardPostEditPage` 함수명 미변경, 런타임 영향 없어 merge 결정)

---

## [F-18] 반응형 레이아웃 (#176)

모바일 우선 반응형 레이아웃 시스템을 구현했다. Tailwind v4 커스텀 브레이크포인트(480px/1080px), 관리자 사이드바 모바일 오버레이, 페이지네이션 반응형, 공개 페이지 max-width 정규화를 완성했다.

**주요 변경 사항:**

- `src/app-layer/style/theme.css` - `@theme` 블록에 커스텀 브레이크포인트 추가 (`--breakpoint-sm: 30rem`, `--breakpoint-lg: 67.5rem`)
- `src/app-layer/style/typography.css` - h1/h2 반응형 크기 (모바일 24px/20px, md+ 30px/26px), `.markdown-content` 테이블 overflow-x, 이미지 max-width
- `src/widgets/admin-sidebar/ui/admin-sidebar.tsx` - 데스크톱 고정 사이드바 + 모바일 오버레이 (`role="dialog"`, `aria-modal`, focus trap, Escape 키, body scroll lock, resize/popstate 핸들러)
- `src/app/manage/layout-shell.tsx` - 햄버거 버튼 (`aria-expanded`, 조건부 `aria-controls`), `didOpenRef` 패턴으로 사이드바 닫힘 시 포커스 반환
- `src/shared/ui/libs/pagination.tsx` - `generatePageNumbers`에 `windowSize` 파라미터 추가. 모바일(±1)/데스크톱(±3) 이중 렌더링, `display: contents` 래퍼로 flex 레이아웃 유지
- 공개 페이지 7개 - 컨테이너 `max-w-[67.5rem] px-4 md:px-6` 적용 (home, post detail, tags, search, popular, categories, guestbook)
- `src/widgets/header/index.tsx` - 헤더 패딩 `px-6` → `px-4 md:px-6`
- 관리자 그리드 3개 파일 - `xl:grid-cols-*` → `lg:grid-cols-*` (1080px 브레이크포인트 통일)

**리뷰 라운드:** 4회
- Round 1: Critical 4건 (focus trap 미구현, `xl:` → `lg:` 미변경, search 페이지 두 번째 return 누락, 헤더 패딩 누락)
- Round 2: Critical 1건 (`<span className="md:hidden">` flex 레이아웃 깨짐 → `contents` 적용), Warning 2건 (search 두 번째 return, 햄버거 포커스 반환)
- Round 3: Critical 1건 (포커스 반환이 마운트 시 실행 → `didOpenRef` 가드), Warning 1건 (`aria-controls` 누락)
- Round 4: Suggestion 1건 (`aria-controls` 조건부 처리) - merge 결정

---

### #221 Design token 동기화 (PR #222 머지)

`docs/client/figma_tokens.json` (2026-03-26 업데이트) 기준으로 `theme.css`와 `typography.css`를 동기화했다.

**주요 변경 사항:**

- `src/app-layer/style/theme.css`
  - `--dark/light-tertiary1/2` → `--dark/light-info1/2` 이름 변경
  - `--dark/light-quaternary1/2` 삭제 (`@theme` 매핑 포함)
  - `--dark/light-warning1/2`, `--dark/light-overlay1`, `--special-code-surface` 추가
  - 색상 값 8개 수정: `light.text.3/4`, `light.border.4`, `light.positive.1`, `dark.text.3/4`, `dark.border.1/4`
  - `@theme` 블록: `--color-info-1/2`, `--color-warning-1/2`, `--color-overlay-1`, `--color-special-code-surface` 추가; `quaternary` 매핑 제거
- `src/app-layer/style/typography.css`
  - `.text-ui-base`, `.text-ui-sm`, `.text-ui-xs` 유틸리티 클래스 추가 (figma_tokens.json `typography.scale.ui` 반영)

**리뷰 라운드:** 0회 (Clean pass)

---

### #178 [F-33c] Client 환경 변수 설정 (PR #223 머지)

`serverFetch()`와 `clientFetch()`의 API URL을 분리했다. 서버 사이드에서는 내부 네트워크 URL(`API_URL`)을 사용하고, 브라우저에서는 공개 URL(`NEXT_PUBLIC_API_URL`)을 사용한다. `API_URL` 미설정 시 `NEXT_PUBLIC_API_URL`로 폴백한다.

**주요 변경 사항:**

- `src/shared/api/client.ts` - `API_URL` 단일 상수를 `PUBLIC_API_URL`(`NEXT_PUBLIC_API_URL` 기반)과 `INTERNAL_API_URL`(`API_URL` 기반, 폴백: `PUBLIC_API_URL`)으로 분리. `serverFetch()`는 `INTERNAL_API_URL`, `clientFetch()`는 `PUBLIC_API_URL` 사용
- `.env.local.example` - 두 변수의 용도와 폴백 동작을 설명하는 인라인 주석 추가

**리뷰 라운드:** 0회 (Clean pass)

---

### #179 [F-36] Footer 콘텐츠 (PR #224 머지)

Footer에 저작권 문구를 추가하고, GitHub 링크를 프로필 URL로 수정했으며, Admin 페이지에서 Footer를 숨겼다.

**주요 변경 사항:**

- `src/widgets/footer/index.tsx` - Logo 제거; `© {year} pyo-sh` 저작권 문구 추가(`new Date().getFullYear()`); GitHub 링크 표시 텍스트를 전체 URL에서 "pyo-sh"로 변경; 소셜 링크에 `aria-label` 추가; `nav aria-label="소셜 링크"` 랜드마크 추가; 상하 패딩 `py-8`(32px), 소셜 링크 간격 `gap-2`(8px), 저작권 상단 여백 `mt-4`(16px)
- `src/shared/constant/url.ts` - `URLS.github` 값을 레포 URL(`pyosh_blog`)에서 프로필 URL(`https://github.com/pyo-sh`)로 변경; 동일해진 `URLS.githubProfile` 제거
- `src/app/(public)/layout.tsx` - NEW: 공개 라우트 전용 레이아웃. Footer를 이 레이아웃에 배치
- `src/app-layer/provider/index.tsx` - Footer import/렌더링 제거 (route group 레이아웃으로 이전)
- 공개 페이지 라우트 7개 (`page.tsx`, `categories/`, `guestbook/`, `popular/`, `posts/`, `search/`, `tags/`) → `app/(public)/`로 이전

**주요 결정:**

- Footer 숨김 방식으로 `usePathname()` 대신 Next.js App Router route group `(public)` 패턴 채택. `usePathname` 방식은 Footer를 클라이언트 컴포넌트로 만들어 불필요한 hydration을 유발하므로, route group 레이아웃 분리로 Footer를 Server Component로 유지.

**리뷰 라운드:** 2회
- Round 1: Warning 1건 (`usePathname` 클라이언트 컴포넌트 → route group 레이아웃으로 교체), Suggestion 1건 (`URLS.githubProfile` 중복 제거)

---

### #184 [F-32] Favicon / Web Manifest (PR #227 머지)

SVG favicon 추가, Web App Manifest를 W3C 권장 형식(`.webmanifest`)으로 변경, 브라우저 테마 색상을 다크/라이트 분리 적용.

**주요 변경 사항:**

- `public/favicon.svg` - NEW: 로고 아이콘 패스 추출. `<style>` 블록에 `prefers-color-scheme` 미디어 쿼리 포함 (라이트: `#232629`, 다크: `#e9eaeb`)
- `public/manifest.webmanifest` - NEW: `manifest.json` 대체. `favicon.ico` type `image/png` → `image/x-icon` 수정, `theme_color` `#8D72E1` → `#8a6fe0`, `background_color` `#FFFFFF` → `#f9f9fa`, SVG 아이콘 항목 추가
- `public/manifest.json` - 삭제
- `src/app/layout.tsx` - SVG favicon을 icons 배열 최상단에 추가, manifest 경로 `/manifest.json` → `/manifest.webmanifest`, `themeColor` 단일 값(`#6200EE`) → 라이트(`#8a6fe0`) / 다크(`#131415`) 분리, `msapplication-TileColor` / `msapplication-TileImage` 메타데이터 제거, `Viewport` 타입 명시

**리뷰 라운드:** 1회 (clean - 지적 없음)
- Round 2: Clean pass

---

### #182 [F-05] 태그별 글 목록 (PR #228 머지)

태그 slug 기반 글 목록 페이지를 완성했다. 기존 구현에서 `PostCard` → `PostListItem` 전환, `Pagination` 사용 패턴을 F-01·F-03·F-05 전체에서 통일했다.

**주요 변경 사항:**

- `src/app/(public)/tags/[slug]/page.tsx` - `PostCard` → `PostListItem` (F-01과 동일), `Pagination`을 `posts.length` 조건 분기 밖으로 이동 (항상 렌더링, 표시 여부는 컴포넌트에 위임)
- `src/app/(public)/categories/[slug]/page.tsx` - `PostCard` → `PostListItem` (태그 페이지와 일관성), `{meta.totalPages > 1 && <Pagination>}` 조건 제거 → 항상 렌더링
- `src/features/post-list/ui/post-list.tsx` - `{meta && meta.totalPages > 1 && <Pagination>}` 조건 제거 → 항상 렌더링, empty 분기를 early return → ternary로 변경
- `stories/app/tag-posts.stories.tsx` - TagPostsPreview 프레젠테이션 컴포넌트로 태그별 글 목록 레이아웃 Storybook story 추가 (Default / WithPagination / Empty / Mobile / DarkMode)
- `stories/mocks/data/tags.ts` - Tag mock 데이터 추가

**Pagination 패턴 통일 근거:** `Pagination` 컴포넌트 내부에 `if (totalPages <= 1) return null` 로직이 있으므로 호출 측에서 이중 조건 체크가 불필요하다.

**리뷰 라운드:** 2회
- Round 1: [WARNING] categories 페이지가 `PostCard`를 그대로 사용해 태그 페이지와 불일치 - `PostListItem`으로 전환
- Round 2: Clean pass

---

### #188 [F-35c] 클라이언트 에러 수집 (PR #230 머지)

React Error Boundary, API 에러 로깅, unhandledrejection 핸들러를 추가해 클라이언트 에러를 체계적으로 수집한다. v1은 콘솔 로깅 기반이다.

**주요 변경 사항:**

- `src/shared/ui/error-boundary.tsx` (신규)
  - `ErrorBoundary` 클래스 컴포넌트 - `componentDidCatch`에서 `[React Error]` 구조화 로깅
  - `retryKey` 카운터 - 재시도 시 children 강제 remount (`<React.Fragment key={retryKey}>`)
  - `ErrorBoundaryWithReset` 래퍼 - `usePathname`으로 라우트 이동 시 자동 리셋 (retryKey도 0으로 초기화)
  - 폴백 UI: `ErrorContent` 컴포넌트 재사용 (badge: "오류가 발생했습니다")
- `src/shared/api/client.ts`
  - `handleResponse`에 optional `context` 파라미터 추가 (`url`, `method`)
  - 5xx 응답: `console.error("[API Error]", ...)` / 4xx 응답: `console.warn("[API Warning]", ...)`
  - `clientFetch`에서 context 전달 (`serverFetch`는 클라이언트 전용 범위라 제외)
- `src/app-layer/provider/index.tsx`
  - `useEffect`로 `unhandledrejection` 이벤트 리스너 등록/정리
- `src/app/layout.tsx`
  - `ErrorBoundaryWithReset`으로 최상위 래핑

**리뷰 라운드:** 4회
- Round 1: 배지 레이블 "500 Server Error" → "오류가 발생했습니다" (클라이언트 에러에 HTTP 500 표기 오류), serverFetch 미로깅 의도 명시 주석 추가
- Round 2: `retryKey` 카운터 추가로 reset 시 children 강제 remount
- Round 3: `ErrorBoundaryWithReset` 래퍼 추가 (라우트 이동 시 자동 리셋), `getDerivedStateFromError`에 `_error` 파라미터 명시
- Round 4: 4xx는 `console.warn` 분기, 라우트 변경 시 `retryKey`도 0으로 초기화
