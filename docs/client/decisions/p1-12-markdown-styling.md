# feat: 마크다운 스타일링

> **Status**: draft
> **Type**: feat
> **Priority**: priority:1
> **Phase**: 1
> **Labels**: feat, priority:1
> **Depends on**: p1-09

## Goal

마크다운 HTML 콘텐츠에 대한 타이포그래피 스타일링

## Context

PostContent에서 렌더링된 HTML에 적절한 타이포그래피 스타일 적용. @tailwindcss/typography 또는 커스텀 CSS.

- Plan reference: `docs/client/plans/phase-1-core.md` (Issue #5 → Task 5)

## Requirements

- Option A (권장): `@tailwindcss/typography` 설치 + CSS에 `@plugin` 추가
- Option B: 커스텀 CSS (`app-layer/style/markdown.css`)
- prose 클래스가 마크다운 HTML에 적용되어야 함

## Scope

- Modify: `package.json` (typography 플러그인 추가 시)
- Modify: `src/app-layer/style/index.css`

## Tech Stack

@tailwindcss/typography (선택)

## Definition of Done

- [ ] 마크다운 타이포그래피 스타일 적용
- [ ] 코드 블록, 제목, 목록 등 기본 요소 스타일 확인
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
