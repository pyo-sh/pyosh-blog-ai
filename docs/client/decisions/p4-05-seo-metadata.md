# feat: SEO 메타데이터 + Open Graph

> **Status**: draft
> **Type**: feat
> **Priority**: priority:3
> **Phase**: 4
> **Labels**: feat, priority:3

## Goal

Next.js metadata API로 페이지별 SEO + Open Graph + RSS 연동

## Context

글로벌 기본 메타데이터 + 글 상세 동적 메타데이터 + RSS link 태그. 서버의 /sitemap.xml, /rss.xml 활용.

- Plan reference: `docs/client/plans/phase-4-extras.md` (Issue #6)

## Requirements

- layout.tsx: 글로벌 metadata (title template, description, OG, RSS alternates)
- posts/[slug]/page.tsx: generateMetadata (동적 title, description, OG image)
- categories/[slug]/page.tsx: generateMetadata (카테고리명)

## Scope

- Modify: `src/app/layout.tsx`
- Modify: `src/app/posts/[slug]/page.tsx`
- Modify: `src/app/categories/[slug]/page.tsx`

## Definition of Done

- [ ] 글로벌 metadata 설정
- [ ] 글 상세 generateMetadata 구현
- [ ] RSS link 태그 추가
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
