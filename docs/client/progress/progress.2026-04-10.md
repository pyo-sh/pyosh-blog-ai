# Client Progress - 2026-04-10

## 완료된 작업

### #298 Category empty state must keep management controls (PR #303 머지)

카테고리 관리 페이지에서 카테고리가 0개일 때도 control box 역할의 toolbar가 계속 노출되도록 empty state 렌더링 경로를 조정했다. `src/features/category-manager/ui/category-tree.tsx`의 조기 반환을 제거하고 toolbar를 상단에 유지한 뒤, empty state는 본문 카드 안에서만 렌더링되도록 분리했다. 1차 동기 `codex` 리뷰 suggestion에서 빈 상태에 일괄 선택/배치 편집 액션이 노출되는 UX 회귀가 지적돼, `src/features/category-manager/ui/category-tree-toolbar.tsx`에서 카테고리 수가 0개일 때 해당 액션을 숨기고 생성 버튼과 표시 토글만 남기도록 보완한 후 재리뷰 clean 상태로 PR을 병합했다.

**주요 변경 사항:**

- `src/features/category-manager/ui/category-tree.tsx`
  - 카테고리 0개 상태에서도 toolbar를 항상 렌더링하도록 early return 제거
  - empty state를 tree content 영역 내부 카드로 옮기고, 빈 트리에서는 drag-and-drop 컨텍스트를 마운트하지 않도록 분기
- `src/features/category-manager/ui/category-tree-toolbar.tsx`
  - `totalCount === 0`일 때 `일괄 선택`과 `배치 편집` 버튼을 숨기고 `카테고리 추가` 버튼은 유지

**검증:**

- `pnpm build`
- `pnpm compile:types` *(build 후 `.next/types` 생성 상태에서 재실행)*
- `pnpm lint` *(저장소 기존 warning 2건 유지)*

**메모:**

- 워크트리에는 의존성이 없어 검증 전에 `pnpm install --frozen-lockfile`로 로컬 `node_modules`를 구성했다.
- `pnpm lint`는 저장소 기존 warning인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용 1건과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.
- PR `#303`은 동기 `codex` 리뷰 2라운드 후 clean 판정으로 병합됐다.

### #297 Admin routes must not render public header (PR #302 머지)

관리자 라우트가 전역 provider에서 주입되는 public `Header`와 admin shell header를 동시에 렌더링하던 문제를 수정했다. public header는 이미 `src/app/(public)/layout-shell.tsx`가 소유하고 있으므로, `src/app-layer/provider/index.tsx`에서 전역 `Header` 렌더링을 제거해 `/manage` 이하에서는 admin chrome만 남도록 정리했다. 동기 `codex` 리뷰 clean 상태를 확인한 뒤 PR을 병합했다.

**주요 변경 사항:**

- `src/app-layer/provider/index.tsx`
  - 전역 provider에서 public `Header`를 제거해 route별 layout shell이 각자 chrome을 책임지도록 정리

**검증:**

- `pnpm compile:types`
- `pnpm lint` *(저장소 기존 warning 2건 유지)*
- `pnpm build` *(저장소 환경 이슈로 실패: `lightningcss.linux-arm64-gnu.node` 누락, `/workspace/client` 의존성 트리에서 재현)*

**메모:**

- `pnpm lint`는 저장소 기존 warning인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용 1건과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.
- PR `#302`는 동기 `codex` 리뷰 clean 판정 후 바로 병합됐다.

### #295 Public shell height and spacing (PR #300 머지)

Public 레이아웃이 viewport 높이를 채우지 못해 콘텐츠가 짧을 때 footer가 본문 바로 아래로 올라오던 문제를 수정했다. `src/app/(public)/layout.tsx`에서 public 트리를 `min-h-screen` 기반의 세로 flex column으로 감싸고, `src/app/(public)/layout-shell.tsx`는 헤더 아래의 콘텐츠 셸이 남은 높이를 차지하도록 `flex-1` 구조로 재구성했다. 1차 자동 리뷰에서 layout-level `<main>`이 기존 route page들의 `<main>`과 중첩된다는 경고가 나와 neutral wrapper로 되돌린 뒤 2차 `codex` 리뷰 clean 상태를 확인하고 PR을 병합했다.

**주요 변경 사항:**

- `src/app/(public)/layout.tsx`
  - public 페이지 전체를 `min-h-screen flex flex-col` 래퍼로 감싸 footer가 viewport 하단까지 밀리도록 조정
- `src/app/(public)/layout-shell.tsx`
  - shell 루트를 `flex flex-1 flex-col`로 바꾸고, 헤더 아래 2-column 콘텐츠 영역이 남은 높이를 점유하도록 수정
  - route page별 landmark 구조를 보존하기 위해 콘텐츠 래퍼는 `<main>` 대신 neutral `<div>`로 유지

**검증:**

- `pnpm compile:types`
- `pnpm lint` *(저장소 기존 warning 2건 유지)*
- `pnpm build` *(저장소 환경 이슈로 실패: `lightningcss.linux-arm64-gnu.node` 누락, `/workspace/client`에서도 동일 재현)*

**메모:**

- `pnpm lint`는 저장소 기존 warning인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용 1건과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.
- PR `#300`은 동기 `codex` 리뷰 2라운드 후 clean 판정으로 병합됐다.

### #296 Admin login screen simplification (PR #301 머지)

`/manage/login` 화면을 로그인 폼에만 집중하는 구조로 단순화했다. 로그인 전용 layout에서 상단/하단 radial gradient 장식과 넓은 콘텐츠 래퍼를 제거하고, 페이지에서 소개용 카피 섹션을 없애 `main > form` 구조만 남겼다. 로그인 폼은 `bg-background-1` 단색 배경 위에서 화면 정중앙에 배치되도록 재구성했고, 헤더 카피도 대시보드 진입 목적만 전달하도록 간결하게 정리했다. 동기 `codex` 리뷰 clean 상태를 확인한 뒤 PR을 병합했다.

**주요 변경 사항:**

- `src/app/manage/login/layout.tsx`
  - 로그인 전용 배경 장식 레이어와 max-width 래퍼를 제거하고 단색 배경만 유지
- `src/app/manage/login/page.tsx`
  - 소개 섹션을 제거하고 로그인 폼만 렌더링하도록 단순화
- `src/features/admin-login/ui/login-form.tsx`
  - 폼을 `min-h-screen` 중앙 정렬 레이아웃으로 변경
  - 로그인 안내 카피를 간결하게 조정

**검증:**

- `pnpm compile:types`
- `pnpm lint` *(저장소 기존 warning 2건 유지)*
- `pnpm build`

**메모:**

- `pnpm lint`는 저장소 기존 warning인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용 1건과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.
- PR `#301`은 동기 `codex` 리뷰 clean 판정 후 바로 병합됐다.
