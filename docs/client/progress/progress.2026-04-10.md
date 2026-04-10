# Client Progress - 2026-04-10

## 완료된 작업

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
