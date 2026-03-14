# Progress: 2026-03-15

## Completed
- [x] #69 조회수 기록 hook + ViewCounter PR #164 머지
  - `src/shared/hooks/use-view-count.ts`에 조회수 기록 훅 추가
  - `src/features/post-detail/ui/view-counter.tsx` 추가, 글 상세 페이지에 연결
  - 같은 세션 내 중복 방지를 위해 `sessionStorage` 기반 `viewed_posts` 사용
  - 검증: `pnpm compile:types && pnpm lint && pnpm build`
  - 리뷰 경고 중 pageview 의미 해석과 빠른 이탈 시 첫 조회 누락 가능성은 요구사항 범위 밖으로 판단하고 현재 구현으로 머지
- [x] #63 SEO 메타데이터 + Open Graph PR #166 머지
  - `src/app/layout.tsx`에 글로벌 metadata, title template, 기본 설명, Open Graph, RSS alternate 링크 추가
  - `src/app/posts/[slug]/page.tsx`에 글 상세 `generateMetadata` 추가, markdown 요약 기반 description 및 OG image 처리
  - `src/app/categories/[slug]/page.tsx`에 카테고리 metadata 추가, paginated canonical URL 및 out-of-range 페이지 404 정합성 보완
  - `src/shared/lib/metadata.ts`에 사이트 URL, metadata base, markdown summary 공용 helper 추가
  - `react` `cache(...)`로 metadata/page 렌더링 간 중복 API 호출 제거
  - 검증: `pnpm compile:types && pnpm lint && pnpm build`

## Issues & Resolutions
- **Issue**: 자동 리뷰가 조회수 의미를 `pageview` 기준으로 해석하며 세션 단위 중복 방지 요구와 충돌
- **Resolution**: 이슈 명세의 `sessionStorage` 기반 세션 중복 방지를 우선하고 현재 구현으로 머지
- **Issue**: 자동 리뷰가 category pagination canonical, metadata/page 간 중복 API 호출, localhost metadataBase fallback을 경고
- **Resolution**: category metadata에서 paginated page 유효성 검증을 추가하고, `cache(...)` 기반 데이터 재사용과 public origin이 설정된 경우에만 절대 metadata URL을 생성하도록 수정

## Next Steps
- [ ] 조회수 집계 의미(`pageview` vs 세션 중복 제거 조회)와 CSRF 선행 요청 허용 여부를 별도 이슈로 정리
