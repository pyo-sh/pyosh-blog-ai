# Progress: 2026-03-08

## Completed
- [x] #24 마크다운 렌더링 유틸리티 구현 - `renderMarkdown(md: string): Promise<string>` 함수 (`src/shared/lib/markdown.ts`)
  - unified 파이프라인: remarkParse → remarkRehype → rehypeShiki → rehypeSanitize → rehypeStringify
  - shiki 테마: `github-dark`
  - sanitize schema 확장: span/pre/code 요소에 `style`, `className` 속성 허용 (shiki 출력 보존)
  - `pnpm compile:types && pnpm lint && pnpm build` 통과

## Next Steps
- [ ] #24 PR 리뷰 및 머지
