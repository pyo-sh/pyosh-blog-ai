# feat: Admin 레이아웃 (사이드바)

> **Status**: draft
> **Type**: feat
> **Priority**: priority:1
> **Phase**: 2
> **Labels**: feat, priority:1
> **Depends on**: p2-02

## Goal

Admin 전용 레이아웃 + 사이드바 네비게이션 구현

## Context

`/dashboard/*` 경로에서 사용되는 Admin 레이아웃. 좌측 사이드바(240px) + 메인 컨텐츠. 공개 헤더/푸터 숨김.

- Plan reference: `docs/client/plans/phase-2-admin.md` (Issue #9 → Task 3)

## Requirements

- AdminSidebar (use client): 대시보드, 글 관리, 카테고리, 댓글, 방명록, 에셋 메뉴
- usePathname 기반 활성 메뉴 하이라이트
- dashboard/layout.tsx: AdminSidebar + main content

## Scope

- Create: `src/widgets/admin-sidebar/ui/admin-sidebar.tsx`
- Create: `src/widgets/admin-sidebar/index.ts`
- Create: `src/app/dashboard/layout.tsx`

## Definition of Done

- [ ] AdminSidebar 위젯 구현 (활성 메뉴 하이라이트)
- [ ] Admin 레이아웃 구현
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
