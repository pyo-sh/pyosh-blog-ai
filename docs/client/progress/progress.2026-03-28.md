# Client Progress - 2026-03-28

## 완료된 작업

### #203 글 관리 벌크 작업 + 미리보기 (PR #247 머지)

글 관리 화면의 남은 클라이언트 제어를 마무리했다. 벌크 액션 바에 공개 여부 변경을 추가해 카테고리/댓글 상태/공개 여부를 한 번에 묶어 전송할 수 있게 했고, 글 미리보기 페이지에서는 `contentModifiedAt`을 직접 설정하거나 제거할 수 있는 컨트롤을 추가한 뒤 자동 리뷰까지 통과시켜 병합했다.

**주요 변경 사항:**

- `src/widgets/admin-post-list/ui/bulk-actions.tsx`
  - 활성 글 벌크 액션 바에 공개 여부 드롭다운을 추가하고, 초기화/적용/확인 모달이 visibility 변경까지 함께 다루도록 확장
- `src/app/manage/posts/page.tsx`, `src/entities/post/model.ts`
  - 벌크 update payload에 `visibility`를 포함하도록 연결해 category/comment status/visibility를 단일 요청 본문으로 보낼 수 있게 정리
- `src/widgets/admin-post-preview/ui/post-preview.tsx`
  - 미리보기 컨트롤 바에 `datetime-local` 기반 수정일 입력, 적용 버튼, 수정일 제거 버튼 추가
  - 현재 글의 `contentModifiedAt`이 있으면 미리보기 메타 영역에도 함께 노출

**검증:**

- `pnpm compile:types`
- `pnpm lint`
- `pnpm build`

**메모:**

- `pnpm lint`는 저장소 기존 warning인 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.
- 클라이언트는 계속 `PATCH /api/admin/posts/bulk` 계약을 사용한다. 현재 로컬 server 트리에는 해당 라우트가 없어 bulk 동작은 server 측 선행 작업에 계속 의존한다.

### #196 댓글 표시 개선 (PR #242 머지)

공개 글 상세의 댓글 섹션을 paginated comment API/meta 기준으로 재정비하고, 자동 리뷰 다라운드에서 나온 edge case를 끝까지 정리한 뒤 PR을 병합했다.

**주요 변경 사항:**

- `src/app/(public)/posts/[slug]/page.tsx`
  - 댓글 초기 로드를 paginated 응답(`data` + `meta`) 기준으로 연결하고, `commentStatus`에 따라 disabled 상태를 SSR에서 반영
  - 마지막 merge 단계에서 `origin/main`의 JSON-LD/TOC 변경과 충돌한 구간을 통합
- `src/features/comment-section/ui/comment-list.tsx`
  - 페이지네이션 UI, reply 펼침/접힘, locked/disabled 상태, secret comment 복원, root/reply delete fallback, hydration-safe secret reveal 로직 추가
  - mutation 성공 후 refetch 실패 시 stale UI가 남지 않도록 로컬 fallback과 meta 보정을 정리
  - 페이지 번호 버튼은 windowed pagination으로 축소해 긴 스레드에서도 DOM/UX 부담을 줄임
- `src/features/comment-section/lib/guest-secret-store.ts`
  - guest secret comment 복원을 위한 sessionStorage 저장 형식을 정리하고, 표시용 이름과 비교용 identity key를 분리
- `src/entities/comment/*`, `stories/features/comment-section.stories.tsx`, `stories/mocks/*`
  - paginated comment meta/client fetch 타입 정리와 story/mocks 업데이트

**리뷰 수정 사항:**

- 삭제된 루트/마지막 답글 삭제 시 페이지 underfill, totalCount drift, refresh 실패 stale UI 문제를 순차적으로 수정
- `locked` 상태에서 삭제까지 막도록 read-only 의미를 맞춤
- guest secret identity가 폼에 자동 주입돼 이전 사용자의 이름/이메일이 보이던 privacy 회귀를 제거
- secret comment 복원을 렌더 시점 storage read에서 `useEffect` 기반 post-mount hydration으로 옮겨 hydration mismatch를 제거
- 마지막 merge 단계에서 `origin/main`과 충돌한 `posts/[slug]/page.tsx`를 수동 병합

**검증:**

- `pnpm build`
- `pnpm compile:types`
- `pnpm lint`

**메모:**

- `pnpm lint`는 저장소 기존 warning인 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.

### #200 글 메타데이터 편집 (PR #245 머지)

관리자 글 작성/수정 화면의 메타데이터 입력을 확장하고, 공개 글 카드/상세 페이지가 새 필드를 실제로 소비하도록 연결한 뒤 자동 리뷰 여러 라운드와 `origin/main` 머지 충돌까지 정리해 병합했다.

**주요 변경 사항:**

- `src/features/post-editor/ui/post-form.tsx`
  - category tree select, tag chip input, thumbnail uploader, summary/description/comment status 입력, 발행 확인 모달, post card preview를 포함하는 메타데이터 편집 흐름으로 확장
  - 자동 summary 생성, 저장/발행 intent 처리, 새 태그 invalidate를 포함한 저장 후속 처리 보강
- `src/features/post-editor/ui/*`
  - `category-tree-select.tsx`, `tag-chip-input.tsx`, `thumbnail-uploader.tsx`, `post-card-preview.tsx`, `publish-confirm-modal.tsx` 추가
  - `markdown-editor.tsx` blur/onChange ref 동기화와 현재 문서 기준 summary 생성 흐름 보완
- `src/entities/post/model.ts`, `src/entities/tag/api.ts`, `src/app/manage/posts/[id]/edit/page.tsx`
  - post create/update payload에 `summary`, `description`, `commentStatus`를 반영하고, 수정 페이지 초기값과 tag query 계약을 맞춤
- `src/features/post-list/ui/post-card.tsx`
  - 공개 post card가 저장된 `post.summary`를 우선 사용하도록 수정
- `src/app/(public)/posts/[slug]/page.tsx`, `src/shared/lib/markdown.ts`, `src/shared/lib/structured-data.ts`, `src/shared/ui/json-ld.tsx`
  - 공개 글 상세에서 `description`을 노출하고 `BlogPosting`/`BreadcrumbList` JSON-LD와 TOC payload를 유지
  - 마지막 `origin/main` 머지에서 들어온 TOC/slug/structured-data 변경과 충돌한 구간을 직접 정리

**리뷰 수정 사항:**

- 실패한 publish/archive intent가 로컬 상태를 잘못 덮어쓰지 않도록 수정
- markdown blur handler가 stale callback/내용을 읽지 않도록 ref 기반으로 정리
- 자동 summary 길이 초과, 이후 content 수정 시 stale 되는 문제, tag 입력 blur 손실, thumbnail URL 적용 시점 문제 수정
- public post card가 summary를 무시하던 회귀와 description 미사용 문제 수정
- public post detail의 `cache()` stale 문제 제거 후, JSON-LD/TOC 복원과 no-store 중복 fetch 회귀를 다시 정리
- 마지막 merge 단계에서 `main`과 충돌한 `posts/[slug]/page.tsx`, `shared/lib/markdown.ts`, `shared/lib/structured-data.ts`를 수동 병합해 PR을 `CLEAN` 상태로 복구

**검증:**

- `pnpm lint`
- `pnpm build`
- `pnpm compile:types`

**메모:**

- `pnpm lint`는 저장소 기존 warning인 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 유지됐다.

### #199 구조화 데이터 (JSON-LD) (PR #246 머지)

홈, 글 상세, 카테고리, 태그 공개 페이지에 JSON-LD 구조화 데이터를 추가하고, 자동 리뷰에서 지적된 성능·FSD 계층·환경 변수 안전성 이슈를 반영한 뒤 병합했다.

**주요 변경 사항:**

- `src/shared/lib/structured-data.ts`
  - `WebSite`, `SearchAction`, `BlogPosting`, `BreadcrumbList` 빌더와 공용 site URL helper를 추가
  - 프로덕션에서 `NEXT_PUBLIC_SITE_URL`이 없으면 잘못된 `localhost` URL을 내보내지 않도록 fail-closed 처리
- `src/shared/ui/json-ld.tsx`
  - Server Component에서 안전하게 JSON-LD `<script>`를 렌더링하는 공용 컴포넌트 추가
- `src/app/(public)/page.tsx`
  - 홈 페이지에 `WebSite` + `SearchAction` 구조화 데이터 삽입
- `src/app/(public)/posts/[slug]/page.tsx`
  - 글 상세 페이지에 `BlogPosting` + `BreadcrumbList` 구조화 데이터 추가
  - `post.category.ancestors`가 없을 때만 카테고리 트리를 병렬 fallback fetch해 breadcrumb 계층 계산
  - `origin/main`의 TOC 변경과 충돌한 머지 구간을 정리해 TOC와 JSON-LD가 함께 동작하도록 통합
- `src/app/(public)/categories/[slug]/page.tsx`, `src/app/(public)/tags/[slug]/page.tsx`
  - 카테고리/태그 페이지 breadcrumb 구조화 데이터 삽입
- `src/entities/post/model.ts`
  - 글 상세 응답의 optional `category.ancestors` 타입 허용
- `package.json`, `pnpm-lock.yaml`
  - `origin/main`의 TOC 머지 과정에서 필요한 `github-slugger`, `mdast-util-to-string`, `rehype-slug` 의존성 동기화

**리뷰 수정 사항:**

- post detail route가 ancestor 데이터가 이미 있을 때도 `fetchCategories()`를 무조건 호출하지 않도록 수정
- `shared` 계층이 `@entities/post`를 참조하지 않도록 structured-data 입력 타입을 shared 내부 최소 인터페이스로 분리
- 잘못된 절대 URL을 발행하지 않도록 `getSiteUrl()`의 localhost fallback을 development 전용으로 제한
- `origin/main`의 TOC 머지 충돌을 직접 해결하고, 누락된 markdown 관련 의존성을 설치해 빌드 회귀를 제거

**검증:**

- `pnpm lint`
- `pnpm build`
- `pnpm compile:types`

**메모:**

- 전체 `pnpm lint`는 저장소 기존 warning인 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 항목 1건이 그대로 남아 있었고, 이번 이슈 범위 밖으로 유지했다.

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
