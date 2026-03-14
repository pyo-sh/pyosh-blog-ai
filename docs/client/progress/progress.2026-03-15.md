# Progress: 2026-03-15

## Completed
- [x] #69 조회수 기록 hook + ViewCounter PR #164 머지
  - `src/shared/hooks/use-view-count.ts`에 조회수 기록 훅 추가
  - `src/features/post-detail/ui/view-counter.tsx` 추가, 글 상세 페이지에 연결
  - 같은 세션 내 중복 방지를 위해 `sessionStorage` 기반 `viewed_posts` 사용
  - 검증: `pnpm compile:types && pnpm lint && pnpm build`
  - 리뷰 경고 중 pageview 의미 해석과 빠른 이탈 시 첫 조회 누락 가능성은 요구사항 범위 밖으로 판단하고 현재 구현으로 머지

## Issues & Resolutions
- **Issue**: 자동 리뷰가 조회수 의미를 `pageview` 기준으로 해석하며 세션 단위 중복 방지 요구와 충돌
- **Resolution**: 이슈 명세의 `sessionStorage` 기반 세션 중복 방지를 우선하고 현재 구현으로 머지

## Next Steps
- [ ] 조회수 집계 의미(`pageview` vs 세션 중복 제거 조회)와 CSRF 선행 요청 허용 여부를 별도 이슈로 정리
