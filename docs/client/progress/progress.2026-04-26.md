# Client Progress - 2026-04-26

## 완료된 작업

### #352 public category tree 정렬/고정 count column 후속 보정 (PR #354 머지)

PR `#353` 머지 후 남아 있던 시각 정렬 문제를 같은 이슈 `#352`에서 한 번 더 보정했다. 이번 변경은 구조를 다시 크게 뒤엎지 않고 `CategoryTree` row contract만 정리하는 쪽으로 좁혔다. sidebar 쪽은 icon slot과 title/count row를 `items-center` 기준으로 다시 맞추고 title line-height를 `1.2`로 낮춰, 8px dot indicator와 텍스트가 실제 시각상 중앙에 맞도록 보정했다. `/categories` overview 쪽은 top-level category title만 요청값대로 `1.0625rem` / `700`으로 올리고, depth indentation이 오른쪽 count 위치를 흔들지 않도록 indent를 icon/content 측에만 남기고 count는 고정 right column으로 분리했다.

동기 `codex` 리뷰 1차 결과는 suggestion 1건뿐이었고, 내용은 hover color inheritance 회귀였다. `titleClassName`이 자식 span에 직접 text color를 주면서 link의 `hover:text-primary-1` 피드백이 title에 전파되지 않던 문제라, span의 base color를 제거해 hover 상속을 복구했다. suggestion-only라 `resolve-skip` 경로로 보정 후 PR `#354`를 머지했다.

**주요 변경 사항:**

- `src/features/category-tree/ui/category-tree.tsx`
  - sidebar/overview row를 고정 `count` column이 있는 grid 구조로 재정렬
  - icon slot과 title/count row를 `items-center` 기준으로 맞추고 title line-height를 `1.2`로 조정
  - `/categories` top-level title만 `1.0625rem` / `700` 적용
  - overview nested wrapper의 폭 감소(`ml/pl`)를 제거해 모든 item의 count x-position을 동일하게 고정
  - review suggestion 반영: title span의 직접 text color를 제거해 link hover color 상속 복구

**검증:**

- `pnpm install --frozen-lockfile`
- `pnpm compile:types`
- `pnpm lint` *(저장소 기존 warning 2건 유지)*
- `pnpm build`

**메모:**

- `pnpm lint`는 기존 warning인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용 1건과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.
- 자동 리뷰는 `0 critical / 0 warning / 1 suggestion`이었고, hover color inheritance만 보정한 뒤 `skipReview=true`로 머지됐다.

### #352 Sidebar 카테고리 UI 재디자인 보정 (PR #353 머지)

최근 public category tree redesign 이후 wireframe과 어긋난 sidebar/categories UI를 보정했다. sidebar leaf category는 부모 toggle과 같은 left slot 안에 8px dot indicator를 두도록 row 구조를 다시 맞춰, 아이콘 위치와 텍스트 간격이 일관되게 정렬되도록 수정했다. `/categories` overview는 top-level count badge의 배경/rounding을 제거하고 title/count typography를 wireframe 밀도에 맞게 낮췄으며, overview 전용 렌더링을 root group + leaf 분기 대신 재귀 `CategoryItem` 기반으로 다시 정리해 중첩 child category도 toggle 가능한 구조로 통합했다.

동시에 Storybook mock category tree에 손자 depth를 추가하고 public `CategoryTree` 전용 story를 만들어 sidebar/overview 둘 다 회귀를 바로 확인할 수 있게 했다. 동기 `codex` 리뷰 1차에서는 recursive overview 도입 후 `getDefaultExpandedSlugs()`와 `모두 펼치기`가 root slug만 수집해 nested expandable group이 기본 확장/expand-all 대상에서 빠지는 warning 1건이 나왔고, visible descendant 전체를 재귀 수집하도록 보정한 뒤 2차 clean 판정으로 PR `#353`이 머지됐다.

**주요 변경 사항:**

- `src/features/category-tree/ui/category-tree.tsx`
  - sidebar leaf row를 toggle slot 기준으로 재정렬하고 8px dot indicator 적용
  - category title/count typography를 wireframe 밀도로 조정
  - overview count badge의 background/radius 제거
  - overview tree를 재귀 `CategoryItem` 구조로 통합해 nested child group toggle 지원
  - overview 기본 확장 slug와 `모두 펼치기` 대상을 visible descendant 전체로 재귀 수집
- `stories/mocks/data/categories.ts`
  - count 값과 손자 depth mock category를 추가해 overview nested toggle 회귀를 재현 가능하게 정리
- `stories/features/category-tree.stories.tsx`
  - public category tree의 sidebar/overview variant를 직접 확인하는 Storybook story 추가

**검증:**

- `pnpm install --frozen-lockfile`
- `pnpm compile:types`
- `pnpm lint` *(저장소 기존 warning 2건 유지)*
- `pnpm build`

**메모:**

- `pnpm lint`는 기존 warning인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용 1건과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.
- issue worktree에는 verify용 의존성이 없어 `pnpm install --frozen-lockfile`로 worktree-local `node_modules`를 먼저 구성했다.

### #348 `/categories` 페이지 재디자인 - 컴팩트 트리 레이아웃 (PR #351 머지)

`/categories` 페이지를 root repo wireframe `docs/client/designs/public/categories.html` 기준의 compact tree archive로 다시 구현했다. 기존 gradient/card 중심 overview를 걷어내고, `ArchiveHeader`는 그대로 유지하면서 제목을 `카테고리`로 맞추고 우측 summary를 `총 N개 분류`로 단순화했다. 본문에는 2칸 stat strip을 추가해 분류 수와 공개 글 수만 남기고, category overview는 top-level group + leaf 구조의 전용 compact tree로 분리했다.

구현은 `CategoryTree`의 sidebar variant와 overview variant를 명확히 분리하는 방향으로 정리했다. sidebar 쪽은 직전 PR #350에서 들어간 leaf row 개선을 유지했고, overview 쪽에만 전체 펼치기/접기, 상위 3개 그룹 기본 확장, muted count pill, compact leaf indentation을 넣었다. 동기 `codex` 리뷰 1차에서는 collapsed group의 hidden link가 tab order에 남는 접근성 warning 1건이 나왔고, child panel을 closed state에서 비노출/비상호작용 상태로 바꿔 재리뷰 clean 판정 후 PR `#351`이 머지됐다.

**주요 변경 사항:**

- `src/app/(public)/categories/page.tsx`
  - header title을 `카테고리`로 조정하고 summary를 `총 N개 분류`로 단순화
  - 2칸 stat strip으로 `분류` / `공개 글` 핵심 수치만 노출
- `src/features/category-tree/ui/category-tree.tsx`
  - overview variant 전용 compact tree UI 추가
  - top-level group toggle, `모두 펼치기` / `모두 접기`, 상위 3개 기본 확장 구현
  - public sidebar leaf row 개선(`solar:record-linear`)과 overview redesign을 같은 파일에서 병합
  - collapsed overview panel의 descendant link를 tab order에서 제거

**검증:**

- `pnpm install --offline --frozen-lockfile`
- `pnpm build`
- `pnpm compile:types`
- `pnpm lint` *(저장소 기존 warning 2건 유지)*

**메모:**

- `pnpm compile:types`는 이 저장소의 `.next/types` 포함 규칙 때문에 `pnpm build` 완료 후 순차 실행했다.
- `pnpm lint`는 기존 warning인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용 1건과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.
- merge 단계에서 `origin/main`의 PR #350 leaf row 변경과 충돌이 발생해, compact overview 변경과 leaf marker 변경을 한 파일에서 재통합한 뒤 정상 머지했다.

### #349 사이드바 카테고리 트리 leaf 아이템 circle indicator 추가 (PR #350 머지)

public sidebar category tree에서 부모 category와 leaf category가 같은 row 구조를 써서 계층 정보가 흐려지던 문제를 정리했다. 구현 기준은 root repo wireframe `docs/client/designs/public/home-page-sidebar.html`의 category section이었고, 요구사항대로 부모 category는 기존 chevron toggle과 expand/collapse 동작을 그대로 유지하면서 leaf category만 direct link row로 분기했다. leaf row는 별도 chevron spacer를 두지 않고 `solar:record-linear` 아이콘을 label 앞에 배치해, 자식이 없는 항목이라는 신호를 더 직접적으로 주도록 맞췄다.

이번 수정은 sidebar variant에만 한정했고 `/categories` overview variant의 compact card/list 표현은 그대로 유지했다. 따라서 홈, 태그 목록, category detail, post detail 등 public sidebar를 공유하는 화면들은 같은 개선을 받되 categories index 자체의 정보 구조는 건드리지 않았다. 동기 `codex` 리뷰는 1라운드 clean 판정이었고 PR `#350`으로 바로 머지됐다.

**주요 변경 사항:**

- `src/features/category-tree/ui/category-tree.tsx`
  - sidebar leaf category를 전용 direct link row로 분기
  - leaf marker로 `solar:record-linear` 아이콘을 추가
  - 부모 category의 chevron toggle/expand state 로직은 유지
  - overview variant는 기존 compact list/card 표현을 그대로 유지

**검증:**

- `pnpm install --frozen-lockfile`
- `pnpm compile:types`
- `pnpm lint` *(저장소 기존 warning 2건 유지)*
- `pnpm build`

**메모:**

- `pnpm lint`는 기존 warning인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용 1건과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.
- 자동 리뷰는 suggestion 없이 clean이어서 resolve 라운드 없이 바로 머지됐다.

### #346 Public 카테고리 내비게이션 UI 정리 (PR #347 머지)

최근 category overview와 public sidebar 개선 이후 커진 category row 표현을 다시 compact한 public navigation 톤으로 조정했다. `CategoryTree`의 sidebar variant에서는 label weight와 vertical padding을 낮추고, 자식이 없는 category도 기존 blank spacer 대신 `aria-hidden` leaf marker를 같은 width slot 안에 렌더링해 chevron이 있는 항목과 정렬을 유지했다. Chevron toggle의 hit area와 expand/collapse 동작은 그대로 유지했다.

`/categories` overview variant는 큰 rounded card와 row shadow를 제거하고 얇은 border, left rail, muted surface, count pill 중심의 compact list item으로 재정리했다. `/categories/[slug]`에서 글이 없는 category empty state는 shared `EmptyState` variant를 바꾸지 않고 해당 route와 Storybook preview에서만 `shadow-none`을 넘겨 public layout과 맞췄다. 동기 `codex` 리뷰는 1라운드 clean 판정이었고 PR `#347`로 머지됐다.

**주요 변경 사항:**

- `src/features/category-tree/ui/category-tree.tsx`
  - sidebar label weight/padding을 줄여 category tree 밀도를 보정
  - leaf category에 non-interactive `aria-hidden` marker 추가
  - overview variant를 shadow 없는 compact bordered list item으로 재정리
- `src/app/(public)/categories/[slug]/page.tsx`
  - category page empty state에 한정해 box shadow 제거
- `stories/app/category-posts.stories.tsx`
  - category posts empty Storybook preview에 동일한 no-shadow 표현 반영

**검증:**

- `pnpm install --frozen-lockfile`
- `pnpm compile:types`
- `pnpm lint` *(저장소 기존 warning 2건 유지)*
- `pnpm build`

**메모:**

- `pnpm lint`는 기존 warning인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용 1건과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.
- 자동 리뷰는 suggestion 없이 clean이어서 resolve 라운드 없이 바로 머지됐다.

### #344 Categories/Tags 헤더 디자인 통일 및 categories 목록/퍼블릭 사이드바 UI 개선 (PR #345 머지)

`/categories`, `/categories/[slug]`, `/tags`의 공개 아카이브 헤더 시각 언어를 하나의 shared component 체계로 정리했다. 기존에는 `/categories/[slug]`만 `ArchiveHeader`를 사용하고 `/categories`, `/tags`는 별도 header markup을 유지하고 있어 title scale, eyebrow, 메타 카운트 배치가 서로 달랐다. 이번 작업에서는 `ArchiveHeader`가 페이지별로 다른 summary와 eyebrow를 받을 수 있도록 일반화하고, `/categories`의 제목을 요구사항대로 `Categories`로 변경해 세 라우트가 같은 구조의 타이틀 시스템을 공유하도록 맞췄다.

동시에 `/categories` 목록에서 쓰는 `CategoryTree`에 overview 전용 표현을 추가해 각 category row가 border, surface, count chip을 가진 카드형 항목으로 보이도록 재구성했다. sidebar에서 쓰는 compact tree 표현은 그대로 유지하고, overview route에서만 더 강한 항목 경계와 depth 가이드를 적용했다. public sidebar는 직전 border-right 추가로 좁아진 desktop 폭을 `234px -> 240px`로 소폭 확장해 내부 gutter가 다시 답답해 보이지 않도록 보정했다. 동기 `codex` 리뷰는 1라운드 clean 판정이었고 PR `#345`로 머지됐다.

**주요 변경 사항:**

- `src/shared/ui/libs/archive-header.tsx`
  - archive header가 page별 eyebrow/summary를 받을 수 있도록 일반화
- `src/app/(public)/categories/page.tsx`
  - `/categories` 제목을 `Categories`로 변경
  - shared archive header를 적용하고 category directory summary를 표시
- `src/app/(public)/tags/page.tsx`
  - `/tags`에 shared archive header를 적용하고 tag count summary를 표시
- `src/features/category-tree/ui/category-tree.tsx`
  - overview variant를 추가해 categories index에서 card형 항목, count chip, nested depth guide를 사용
  - sidebar에서는 기존 compact variant를 유지
- `src/app/(public)/layout-shell.tsx`
  - desktop public sidebar width를 `240px`로 확장

**검증:**

- `pnpm compile:types`
- `pnpm lint` *(저장소 기존 warning 2건 유지)*
- `pnpm build`

**메모:**

- `pnpm lint`는 기존 warning인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용 1건과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.
- 자동 리뷰는 suggestion 없이 clean이어서 추가 resolve 라운드 없이 바로 머지됐다.

### #342 카테고리 전체보기 500 오류 및 public 사이드바 구분선 위치 조정 (PR #343 머지)

`/categories` 전체보기 페이지가 서버 렌더링 중 500으로 실패하던 문제를 수정했다. 원인은 server component인 `src/app/(public)/categories/page.tsx`가 `"use client"` 모듈인 `CategoryTree` 파일에서 함께 export된 `countVisibleCategories()`를 직접 호출하고 있던 점이었다. 이 함수는 public 사이드바처럼 client component 안에서는 문제없었지만, 서버 라우트에서는 client export를 실행할 수 없어 카테고리 전체보기 진입 시 런타임 오류로 이어졌다. 수정은 순수 재귀 count 로직을 `src/features/category-tree/lib/category-counts.ts`로 분리해 server/client 양쪽에서 공용으로 쓰도록 정리하는 방향으로 진행했다.

동시에 이슈에 포함된 UI 요구사항에 맞춰 desktop public sidebar의 약한 구분선을 `aside` 외곽이 아니라 내부 wrapper에 적용하도록 레이아웃을 조정했다. 자동 리뷰 1차에서는 divider를 안쪽으로 옮긴 뒤 outer `pr-8`을 그대로 둬 gutter가 두 배로 벌어지는 warning이 나왔고, follow-up 커밋에서 outer padding을 제거해 폭 회귀 없이 구분선 위치만 바뀌도록 마무리했다. PR `#343`은 동기 `codex` 리뷰 2라운드 후 clean 판정으로 병합됐다.

**주요 변경 사항:**

- `src/features/category-tree/lib/category-counts.ts`
  - visible category node 수와 published post 수를 세는 순수 helper를 분리
- `src/features/category-tree/index.ts`
  - counting helper를 client component export와 분리해 re-export
- `src/features/category-tree/ui/category-tree.tsx`
  - overview count 계산을 공용 helper로 통일
- `src/app/(public)/categories/page.tsx`
  - server route가 client module 함수를 직접 호출하지 않도록 정리
- `src/app/(public)/layout-shell.tsx`
  - desktop sidebar divider를 inner wrapper에 적용하고 중복 gutter 제거

**검증:**

- `pnpm install --frozen-lockfile`
- `pnpm compile:types`
- `pnpm lint` *(저장소 기존 warning 2건 유지)*
- `pnpm build`

**메모:**

- `pnpm lint`는 저장소 기존 warning인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용 1건과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.
- 최초 구현 커밋 `c5ae16e` 뒤 자동 리뷰 warning 1건을 반영해 `d7c1fd1`로 divider spacing을 보정했고, 이후 재리뷰 clean으로 병합했다.

### #340 Public sidebar 카테고리 섹션 정리 및 active path auto-expand (PR #341 머지)

public sidebar의 category 섹션을 카테고리 탐색 중심 흐름으로 정리했다. 섹션 제목을 `카테고리 (N)`으로 단축하고 `/categories`로 이동하는 `전체보기` 액션을 추가했으며, category tree는 기본적으로 모두 접힌 상태에서 시작하도록 바꿨다. `/categories/[slug]`와 `/posts/[slug]`에서는 현재 카테고리 경로만 자동으로 펼쳐지도록 route별 sidebar seed 데이터를 내려 보내고, tree 내부에서는 그 seed를 초기 상태로만 사용해 사용자가 직접 토글한 이후 상태를 같은 렌더링 흐름에서 덮어쓰지 않도록 분리했다.

자동 리뷰 1차에서는 `CategoryTree`의 `initialExpandedSlugs = []` 기본값이 prop 생략 호출자에서 무한 렌더 루프를 만들 수 있다는 warning이 나왔다. 이에 따라 안정적인 module-level 빈 배열 fallback으로 수정하고, 다시 `compile:types`, `lint`, `build`를 확인한 뒤 재리뷰 clean 판정으로 PR `#341`를 머지했다.

**주요 변경 사항:**

- `src/widgets/public-sidebar/ui/public-sidebar.tsx`
  - category 섹션 제목을 `카테고리 (N)`으로 변경
  - `/categories`로 이동하는 `전체보기` 액션 추가
  - post/category page에서 주입한 sidebar category path JSON을 읽어 tree 초기 확장 slug를 계산
- `src/features/category-tree/ui/category-tree.tsx`
  - 토글 상태를 item local state에서 tree root state로 승격
  - route seed 기반 `initialExpandedSlugs` 지원
  - prop 생략 시 무한 렌더를 막는 stable empty fallback 추가
- `src/app/(public)/posts/[slug]/page.tsx`
  - 현재 글 category path slug를 sidebar용 JSON script로 주입
- `src/app/(public)/categories/[slug]/page.tsx`
  - 현재 category path slug를 sidebar용 JSON script로 주입

**검증:**

- `pnpm install`
- `pnpm build`
- `pnpm compile:types`
- `pnpm lint` *(저장소 기존 warning 2건 유지)*

**메모:**

- `pnpm compile:types`는 이 저장소의 `.next/types` 포함 규칙 때문에 `pnpm build` 완료 후 순차 실행했다.
- 남아 있는 lint warning 2건은 기존 이슈와 동일하게 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용이다.

### #337 public 비밀글 안내 문구 한글화 (PR #339 머지)

public 댓글 비밀글이 영어 문구 `This comment is secret.` 으로 노출되던 문제를 client 이슈 `#337` 기준으로 정리했다. 클라이언트 코드 검색 결과 비밀글 마스크 판별은 `src/features/comment-section/ui/comment-list.tsx` 한 곳에서만 이뤄지고 있었고, 여기서는 한국어 sentinel `비공개 메시지입니다` 만 비밀글 마스크로 취급하고 있었다. 이번 수정으로 legacy 영어/한국어 마스크 문자열은 모두 비밀글로 인식하되, 실제 사용자 표시 문구는 항상 `비공개입니다.` 로 통일했다.

자동 리뷰 1차에서는 새 표시 문구 자체를 sentinel alias에 포함하면 실제 댓글 본문과 충돌할 수 있다는 suggestion이 나왔다. 이에 따라 판별 alias는 기존에 알려진 영어/이전 한국어 마스크만 유지하고, 렌더링 시에만 새 문구 `비공개입니다.` 를 사용하도록 보정했다. 재리뷰 후 clean 판정으로 PR `#339`를 머지했다.

**주요 변경 사항:**

- `src/features/comment-section/ui/comment-list.tsx`
  - 비밀글 표시 문구를 `비공개입니다.` 로 통일
  - legacy 영어 마스크 `This comment is secret.` 지원 추가
  - 이전 한국어 마스크 `비공개 메시지입니다` 도 계속 지원
  - 표시 문구와 비밀글 판별 sentinel을 분리해 실제 댓글 본문과의 충돌 가능성 축소

**검증:**

- `pnpm install --frozen-lockfile`
- `pnpm lint` *(저장소 기존 warning 2건 유지)*
- `pnpm build`
- `pnpm compile:types`

**메모:**

- client 코드 기준 동일 런타임 판별 지점은 `comment-list.tsx` 한 곳뿐이었다.
- `pnpm lint`는 저장소 기존 warning인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용 1건과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.
