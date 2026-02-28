# feat: 마크다운 에디터 + 프리뷰 feature

> **Status**: draft
> **Type**: feat
> **Priority**: priority:1
> **Phase**: 2
> **Labels**: feat, priority:1
> **Depends on**: p2-10

## Goal

Admin 글 작성에 사용하는 마크다운 에디터(textarea) + 실시간 프리뷰 + PostForm 구현

## Context

순수 textarea 에디터 + 클라이언트 사이드 마크다운 렌더링 프리뷰. 좌우 분할 레이아웃. 카테고리/태그/상태 메타 정보 폼 포함.

- Plan reference: `docs/client/plans/phase-2-admin.md` (Issue #12 → Task 2)

## Requirements

- MarkdownEditor: textarea, value/onChange
- MarkdownPreview: 300ms debounce로 마크다운 → HTML 렌더링 (클라이언트 사이드)
- PostForm: 제목, 카테고리 드롭다운, 태그(쉼표 구분), 상태, 가시성, 썸네일 URL, 에디터+프리뷰(좌우 60vh), 제출/취소 버튼
- TanStack Query로 카테고리 목록 fetch
- createPost/updatePost mutation

## Scope

- Create: `src/features/post-editor/ui/markdown-editor.tsx`
- Create: `src/features/post-editor/ui/markdown-preview.tsx`
- Create: `src/features/post-editor/ui/post-form.tsx`
- Create: `src/features/post-editor/index.ts`

## Definition of Done

- [ ] MarkdownEditor textarea 구현
- [ ] MarkdownPreview debounce 렌더링 구현
- [ ] PostForm (메타 정보 + 에디터/프리뷰) 구현
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
