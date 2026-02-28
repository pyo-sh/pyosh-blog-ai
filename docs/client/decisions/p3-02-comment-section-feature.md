# feat: CommentSection feature (Item/Form/List)

> **Status**: draft
> **Type**: feat
> **Priority**: priority:2
> **Phase**: 3
> **Labels**: feat, priority:2
> **Depends on**: p3-01

## Goal

댓글 표시/작성/삭제 UI 컴포넌트 구현

## Context

계층형 댓글 렌더링, 게스트 작성 폼, 답글, 비밀 댓글 마스킹, 삭제(비밀번호 확인).

- Plan reference: `docs/client/plans/phase-3-public.md` (Issue #13 → Task 2)

## Requirements

- CommentItem: 작성자, 날짜, 본문 (삭제됨/비밀 마스킹), 답글/삭제 버튼, 재귀 replies 렌더링
- CommentForm: 이름, 이메일, 비밀번호, 본문, 비밀 여부 체크박스, parentId/replyToCommentId 지원
- CommentList: 댓글 목록 + 답글 타겟 상태 + 삭제 모달 (비밀번호 입력) + 메인 작성 폼

## Scope

- Create: `src/features/comment-section/ui/comment-item.tsx`
- Create: `src/features/comment-section/ui/comment-form.tsx`
- Create: `src/features/comment-section/ui/comment-list.tsx`
- Create: `src/features/comment-section/index.ts`

## Definition of Done

- [ ] CommentItem (계층형, 마스킹) 구현
- [ ] CommentForm (게스트 입력) 구현
- [ ] CommentList (오케스트레이터) 구현
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
