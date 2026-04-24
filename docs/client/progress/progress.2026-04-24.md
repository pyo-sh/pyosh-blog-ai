# Client Progress - 2026-04-24

## 완료된 작업

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
- `pnpm build` *(환경 이슈로 실패: `lightningcss.linux-arm64-gnu.node` 누락, 변경분과 무관하게 `/workspace/client`에서도 동일하게 재현)*

**메모:**

- 이 변경으로 public 사이드바의 "분류 전체보기" 링크는 더 이상 존재하지 않는 경로를 prefetch하지 않는다.
- `pnpm lint` warning 2건은 기존 저장소 상태로, `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용과 `src/shared/ui/error-boundary.tsx`의 미사용 인자다.
