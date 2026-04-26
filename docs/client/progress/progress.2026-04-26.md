# Client Progress - 2026-04-26

## 완료된 작업

### #336 public 사이드바 모바일 헤더 겹침 및 데스크톱 border-right 정렬 수정 (PR #338 머지)

public 레이아웃의 모바일 슬라이드 인 사이드바가 고정 헤더 아래에서 시작하지 않아 패널 상단 콘텐츠가 헤더와 겹치던 문제를 수정했다. 동시에 데스크톱 public 사이드바는 기존 `gap + pr` 기반 간격 구조를 정리하고 실제 `border-right` 구분선을 자연스럽게 배치하도록 레이아웃 spacing을 재배치했다. 이번 수정에서는 헤더가 측정한 실제 높이를 CSS 변수로 노출하고, `SlideInPanel`이 선택적으로 상단 오프셋을 받을 수 있게 해 public 모바일 패널이 헤더 높이를 그대로 따르도록 맞췄다. PR `#338`은 동기 `codex` 리뷰 1라운드 후 clean 판정으로 병합됐다.

**주요 변경 사항:**

- `src/shared/ui/libs/slide-in-panel.tsx`
  - 슬라이드 인 패널에 선택적 `topOffset` prop 추가
  - 상단 오프셋이 필요한 패널이 기존 caller를 깨지 않고 고정 헤더 아래에서 시작할 수 있게 정리
- `src/widgets/header/index.tsx`
  - 측정된 헤더 높이를 `--site-header-height` CSS 변수로 노출
  - public 모바일 사이드바가 실제 헤더 높이를 그대로 참조하도록 연결
- `src/app/(public)/layout-shell.tsx`
  - 모바일 public 사이드바 패널에 헤더 높이 기반 `topOffset` 전달
  - 데스크톱 sidebar/main 간격 구조를 `gap` 중심에서 `border-right + padding` 구조로 재배치

**검증:**

- `pnpm install`
- `pnpm compile:types`
- `pnpm lint` *(저장소 기존 warning 2건 유지)*
- `pnpm build`
- 동기 `codex` PR 리뷰 1라운드
- 리뷰 결과: `0 critical / 0 warning / 0 suggestion`

**메모:**

- `pnpm lint` warning은 기존 항목인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 2건만 남았다.
- issue worktree에는 의존성이 없어 verify 전에 worktree-local `pnpm install`이 필요했다.
