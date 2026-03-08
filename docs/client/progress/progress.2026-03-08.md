# Progress: 2026-03-08

## Completed
- [x] #24 마크다운 렌더링 유틸리티 구현 - `renderMarkdown(md: string): Promise<string>` 함수 (`src/shared/lib/markdown.ts`)
  - unified 파이프라인: remarkParse → remarkRehype → rehypeShiki → rehypeSanitize → rehypeStringify
  - shiki 테마: `github-dark`
  - sanitize schema 확장: span/pre/code 요소에 `style`, `className` 속성 허용 (shiki 출력 보존)
  - `pnpm compile:types && pnpm lint && pnpm build` 통과
- [x] #29 Category entity 타입 + API 구현
  - `src/entities/category/model.ts`: `Category` 인터페이스 (id, parentId, name, slug, sortOrder, isVisible, createdAt, updatedAt, children 재귀)
  - `src/entities/category/api.ts`: `fetchCategories(cookieHeader?)` - serverFetch 사용
  - `src/entities/category/index.ts`: barrel export
  - `pnpm compile:types && pnpm lint && pnpm build` 통과
- [x] #30 PostContent + PostNavigation 컴포넌트 구현 (`src/features/post-detail/`)
  - `post-content.tsx`: async Server Component, `renderMarkdown` 호출, `prose` 클래스 적용, `dangerouslySetInnerHTML`
  - `post-navigation.tsx`: prevPost/nextPost 링크 카드 (없으면 빈 공간)
  - `index.ts`: barrel export
  - worktree는 `feat/issue-24-markdown-renderer` 기반 (renderMarkdown 의존성 미머지 상태)
  - `pnpm compile:types && pnpm lint && pnpm build` 통과

## Next Steps
- [ ] #24 PR 리뷰 및 머지
- [ ] #29 PR 리뷰 및 머지
- [ ] #30 PR 리뷰 및 머지
