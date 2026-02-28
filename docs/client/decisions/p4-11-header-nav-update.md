# feat: 헤더 네비게이션 업데이트

> **Status**: draft
> **Type**: feat
> **Priority**: priority:3
> **Phase**: 4
> **Labels**: feat, priority:3

## Goal

Phase 1-4에서 추가된 모든 공개 페이지를 헤더 네비게이션에 반영

## Context

현재 헤더에는 기본 네비게이션만 있음. 인기, 태그, 방명록 링크 추가 필요.

- Plan reference: `docs/client/plans/phase-4-extras.md` (헤더 네비게이션 업데이트 섹션)

## Requirements

- navItems: 홈(/), 인기(/popular), 태그(/tags), 방명록(/guestbook)
- 기존 navigation.tsx 수정

## Scope

- Modify: `src/widgets/header/navigation.tsx`

## Definition of Done

- [ ] 헤더 네비게이션 업데이트
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
