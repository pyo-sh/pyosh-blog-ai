# Progress: 2026-03-14

## Completed
- [x] #28 CategoryNav 위젯 PR #134 머지
  - PR: `feat: add category nav widget (#28)`
  - merge target: `main`
  - 구현: `src/widgets/category-nav/ui/category-nav.tsx`, `src/widgets/category-nav/index.ts`
  - review fix: `src/app/categories/[slug]/page.tsx` 추가로 CategoryNav pill 링크가 실제 public route로 해석되도록 보완
  - merge: squash merge, merge commit `c1432e09b72b9fc504c372444c82cd4d5ccff7d1`
  - branch: `feat/issue-28-category-nav` (remote branch deleted, local issue worktree cleanup pending at log time)
- [x] #27 글로벌 loading/error/not-found 페이지 PR #133 머지
  - PR: `feat: add global app states (#27)`
  - merge target: `main`
  - 구현: `src/app/loading.tsx`, `src/app/error.tsx`, `src/app/not-found.tsx`
  - review fix 1: `src/app/dashboard/loading.tsx` 추가로 대시보드가 public feed skeleton을 상속하지 않도록 분리
  - review fix 2: `src/app/global-error.tsx` 추가로 root layout / provider 초기화 실패에도 커스텀 전역 에러 UI 제공
  - merge: squash merge, merge commit `7a7e21c58f0a4ba4a4407de78a58749fb837919f`
  - branch: `feat/issue-27-app-states` (PR merge 후 remote branch deleted, local issue worktree cleanup pending at log time)
- [x] #26 Public Post API functions PR #131 머지
  - PR: `feat: add post API functions (#26)`
  - merge: squash merge, merge commit `b56d8d2d9e25e095c8bfe1f81876ce5f779e3e05`
  - branch: `feat/issue-26-post-api-functions` (issue worktree cleaned up after merge)
- [x] #32 Pagination 공통 컴포넌트 PR #128 머지
  - PR: `feat: Pagination 공통 컴포넌트 (#32)`
  - merge: squash merge, merge commit `da8901d7ab14efbf3bfd97daa7bd6e7e57e0dd00`
  - branch: `feat/pagination-component` (remote branch deleted attempt completed, local branch deletion skipped because the branch is still attached to `/workspace/.workspace/worktrees/client/feat-pagination-component`)
- [x] #30 PostContent + PostNavigation PR #132 머지
  - PR: `feat: PostContent + PostNavigation 컴포넌트 (#30)`
  - merge target: `main`
  - review fix: replace undefined `prose` usage with project-owned `markdown-content` styles in `src/app-layer/style/typography.css`
  - merge: squash merge, merge commit `d2067fcd6fb88fb9b3b2b343329b4f2fcebb6f19`
  - branch: `feat/issue-30-post-content-nav` (remote branch deleted, local worktrees cleaned up)

## Discoveries
- The initial `CategoryNav` widget matched the issue text but still needed a real `src/app/categories/[slug]` route in this app tree; otherwise every category pill except "전체" would land on a 404.
- In this repo, `pnpm compile:types` can fail in a fresh worktree before a build because `tsconfig.json` includes `.next/types/**/*.ts`; running `pnpm build` first generates the missing route type files, after which `tsc --noEmit` succeeds.
- Next.js App Router에서 `app/error.tsx`는 root layout 위에서 발생한 실패를 잡지 않으므로, 진짜 전역 런타임 에러 화면이 필요하면 `app/global-error.tsx`를 별도로 둬야 한다.
- root `app/loading.tsx`는 하위 모든 세그먼트에 전파되므로, public 영역 전용 스켈레톤을 둘 때는 dashboard 같은 별도 섹션에 route-local loading boundary를 추가해야 fallback mismatch를 막을 수 있다.
- Public post reads fit cleanly into the existing `src/entities/post/api.ts` module; a separate public/admin split was unnecessary for this scope.
- A fresh issue worktree did not have dependencies installed, so `pnpm install --frozen-lockfile` was required before `pnpm compile:types && pnpm lint && pnpm build` could run.
- The Codex review on PR #131 reported `[CRITICAL]=0`, `[WARNING]=0`, `[SUGGESTION]=0`, so the pipeline advanced directly to merge without a resolve round.
- Pagination UI was already re-reviewed after the token-name fix and had no remaining CRITICAL/WARNING/SUGGESTION findings before merge.
- GitHub merged the PR at `2026-03-13T19:02:47Z`, which is `2026-03-14 04:02:47` in KST.
- The original `#30` implementation existed on a stacked branch that had been merged into `feat/issue-24-markdown-renderer`, but not opened as a clean PR against `main`.
- Replaying only the isolated `#30` commit onto a fresh `main` branch produced a clean PR path and avoided carrying stale stacked-branch changes.
- The review on PR #132 surfaced a real styling gap: this repo does not define Tailwind Typography’s `prose` class, so markdown rendering needed project-owned CSS utilities instead.
- The verification flow in both the fresh issue worktree and the resolve worktree required `pnpm install` before `pnpm compile:types && pnpm lint && pnpm build`.
- GitHub marked PR #132 as merged at `2026-03-13T20:48:25Z`, which is `2026-03-14 05:48:25` in KST.

## Issues & Resolutions
- **Issue**: `CategoryNav` 위젯의 `/categories/[slug]` 링크가 실제 app router 경로와 맞지 않아 PR review에서 즉시 404 위험이 지적되었다.
- **Resolution**: `src/app/categories/[slug]/page.tsx`를 추가하고, visible category slug를 검증한 뒤 유효하지 않은 slug에는 `notFound()`를 반환하도록 보완했다.
- **Issue**: review fix 검증 시 fresh worktree의 `pnpm compile:types`가 `.next/types/app/...` 파일이 없다는 이유로 먼저 실패했다.
- **Resolution**: worktree에서 `pnpm build`로 Next route types를 생성한 뒤 `pnpm compile:types`를 재실행해 통과시켰다.
- **Issue**: Root `src/app/loading.tsx` 때문에 `/dashboard` 로딩 시 public post-list skeleton이 잠시 표시되었다.
- **Resolution**: `src/app/dashboard/loading.tsx`를 추가해 admin 라우트 트리에 전용 loading fallback을 분리했다.
- **Issue**: `src/app/error.tsx`만으로는 `src/app/layout.tsx` 또는 전역 provider 초기화 단계에서 발생한 런타임 에러를 처리할 수 없었다.
- **Resolution**: `src/app/global-error.tsx`를 추가해 앱 전체에 적용되는 runtime error boundary를 제공했다.
- **Issue**: `gh pr merge --delete-branch` could not remove the local branch because `feat/pagination-component` is checked out in an existing client worktree.
- **Resolution**: kept the active worktree branch intact and verified that the PR itself was merged successfully on GitHub.
- **Issue**: The original `#30` branch was stacked on top of `#24`, so the already-merged feature work was not represented by a clean PR to `main`.
- **Resolution**: created a fresh issue branch from `main`, cherry-picked only the `#30` feature commit, opened PR #132, then addressed the review warning with project-owned markdown styles before merge.

## Next Steps
- [ ] Wire `PostContent` and `PostNavigation` into the actual post detail route once the page composition task is active.

## Notes
- Related PR: #134
- Related Issue: #28
- Related PR: #133
- Related Issue: #27
- Related PR: #131
- Related Issue: #26
- Related PR: #128
- Related PR: #132
- Related Issue: #32
- Related Issue: #30
