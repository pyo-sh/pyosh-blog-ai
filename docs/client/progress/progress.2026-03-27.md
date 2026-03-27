# Client Progress - 2026-03-27

## 완료된 작업

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
