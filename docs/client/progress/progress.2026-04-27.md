# Progress: 2026-04-27

## Completed

- [x] #352 public category tree renderer를 sidebar 전용 view와 `/categories` overview 전용 view로 분리
- [x] Sidebar category tree의 row height, toggle icon slot, text/icon vertical alignment, hover border behavior를 sidebar 요구사항 기준으로 정리
- [x] `/categories` overview tree의 top-level title typography, fixed count column, icon/title/count vertical alignment, child indentation, Link-hover row background behavior를 overview 요구사항 기준으로 정리
- [x] `/categories` page Storybook story를 추가하고 기존 category-tree story가 명시적인 sidebar/overview 컴포넌트를 렌더링하도록 갱신
- [x] 전체 변경사항을 단일 커밋 `8106e6f`로 정리하고 PR #356 생성

## Discoveries

- 기존 `CategoryTree`는 `variant`/`isOverview` 계열 조건으로 sidebar와 `/categories` 화면을 동시에 처리해, 한쪽 UI 수정이 다른 화면의 spacing, icon size, row height에 영향을 주기 쉬운 구조였다.
- 렌더링 view는 분리하되 visible tree 계산과 expanded slug state는 `lib`로 추출해 공유하면 UI 결합을 줄이면서 동작 로직 중복은 피할 수 있다.

## Issues & Resolutions

- **Issue**: `pnpm build`가 로컬 `node_modules`의 `lightningcss` optional native package 누락으로 실패했다.
- **Resolution**: `CI=true pnpm install --force --frozen-lockfile`로 lockfile을 유지한 채 native optional dependency를 복구한 뒤 `pnpm build`를 통과시켰다.
- **Issue**: Storybook typecheck에는 기존 `Post` export mismatch 오류가 남아 있었다.
- **Resolution**: 새 `/categories` story 자체의 타입 오류는 발생하지 않았고, 별도 기존 Storybook typing 이슈로 분리해서 볼 수 있도록 기록했다.

## Verification

- [x] `pnpm compile:types`
- [x] `pnpm lint`
- [x] `pnpm build`

## Next Steps

- [ ] PR #356 merge 후 Issue #352 close 상태 확인
