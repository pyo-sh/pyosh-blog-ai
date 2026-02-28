# feat: 헤더 검색바

> **Status**: draft
> **Type**: feat
> **Priority**: priority:3
> **Phase**: 4
> **Labels**: feat, priority:3
> **Depends on**: p4-06

## Goal

헤더에 검색 아이콘 + 토글 검색바 추가

## Context

검색 아이콘 클릭 → 입력 필드 토글 → Enter 시 /search?q=... 이동.

- Plan reference: `docs/client/plans/phase-4-extras.md` (검색 기능 → Task 2)

## Requirements

- SearchBar (use client): 검색 아이콘 버튼 + 토글 입력 필드
- Enter/submit → router.push(`/search?q=...`)
- header 위젯에 통합

## Scope

- Create: `src/widgets/header/search-bar.tsx`
- Modify: `src/widgets/header/index.tsx`

## Definition of Done

- [ ] SearchBar 컴포넌트 구현
- [ ] 헤더에 통합
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
