# feat: 마크다운 렌더링 유틸리티 (shiki)

> **Status**: draft
> **Type**: feat
> **Priority**: priority:1
> **Phase**: 1
> **Labels**: feat, priority:1
> **Depends on**: p1-08

## Goal

unified 기반 마크다운 → HTML 변환 유틸리티 함수 구현

## Context

서버 사이드에서 마크다운을 HTML로 변환. shiki로 코드 하이라이팅. rehype-sanitize로 XSS 방지 (shiki style 속성 허용).

- Plan reference: `docs/client/plans/phase-1-core.md` (Issue #5 → Task 2)

## Requirements

- `renderMarkdown(md: string): Promise<string>` 함수
- 파이프라인: remarkParse → remarkRehype → rehypeShiki → rehypeSanitize → rehypeStringify
- shiki 테마: `github-dark`
- sanitize schema에서 shiki의 style, className 속성 허용

## Scope

- Create: `src/shared/lib/markdown.ts`

## Definition of Done

- [ ] renderMarkdown 함수 구현
- [ ] shiki 코드 하이라이팅 동작
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
