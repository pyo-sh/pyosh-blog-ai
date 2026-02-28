# feat: PostContent + PostNavigation 컴포넌트

> **Status**: draft
> **Type**: feat
> **Priority**: priority:1
> **Phase**: 1
> **Labels**: feat, priority:1
> **Depends on**: p1-02, p1-09

## Goal

글 본문 렌더링 컴포넌트(async Server Component)와 이전/다음 글 네비게이션 구현

## Context

PostContent는 renderMarkdown을 호출하는 async Server Component. PostNavigation은 prevPost/nextPost 링크.

- Plan reference: `docs/client/plans/phase-1-core.md` (Issue #5 → Task 3)

## Requirements

- `PostContent`: contentMd를 받아 서버에서 HTML 렌더링 후 dangerouslySetInnerHTML. prose 클래스 적용.
- `PostNavigation`: prevPost/nextPost가 있으면 링크 카드 표시. 없으면 빈 공간.

## Scope

- Create: `src/features/post-detail/ui/post-content.tsx`
- Create: `src/features/post-detail/ui/post-navigation.tsx`
- Create: `src/features/post-detail/index.ts`

## Definition of Done

- [ ] PostContent async Server Component 구현
- [ ] PostNavigation 컴포넌트 구현
- [ ] barrel export 설정
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
