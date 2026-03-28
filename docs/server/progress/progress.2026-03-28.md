# Progress: 2026-03-28

## Completed

- [x] Issue #67: Admin 글 목록 조회수/댓글수 정렬 지원 + PR #68 merge 완료
  - `AdminPostListQuerySchema`에 `totalPageviews`, `commentCount` 정렬 키 추가
  - `PostService.getPostList()`에서 stats/comment 집계 서브쿼리 기반 정렬을 추가해 `asc|desc`와 기존 필터/페이지네이션을 유지
  - `test/routes/posts.test.ts`에 조회수/댓글수 정렬 asc/desc 및 filter/pagination 호환 통합 테스트 추가
  - Codex review clean 후 PR #68 merge

- [x] Issue #191: PR #66 에셋 업로드 검증 강화 리뷰 반영 + merge 완료
  - `image/webp` 검증을 `RIFF....WEBP` 시그니처까지 확인하도록 보강
  - `image/svg+xml`은 지원을 유지하되, active content를 차단하는 좁은 safe subset 검증 추가
  - SVG 검증은 XML numeric entity를 디코드한 뒤 `javascript:` URL, 이벤트 핸들러, `script`, `foreignObject`, 링크/외부참조 성격 요소 및 속성을 차단
  - `test/routes/assets.test.ts`에 안전한 SVG 허용, active SVG 차단, entity-encoded scriptable URL 차단, fake WebP 차단 케이스 추가
  - 리뷰 2라운드 반영 후 clean review 확인, PR #66 merge

## Notes

- 관련 PR: [PR #68](https://github.com/pyo-sh/pyosh-blog-be/pull/68)
- 관련 이슈: #67
- 검증 메모:
  - `test/routes/posts.test.ts` 67개 통과 확인
  - 전체 `pnpm test`는 이 작업과 무관하게 기존 guestbook 테스트가 `site_settings_tb` 누락으로 실패함
- 관련 PR: [PR #66](https://github.com/pyo-sh/pyosh-blog-be/pull/66)
- 관련 이슈: #191
- 검증 메모:
  - `assets.test.ts` 20개 통과 확인
  - 전체 test 실행은 repo 기존 guestbook/stats 실패로 green은 아니었음
