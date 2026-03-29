# Progress: 2026-03-28

## Completed

- [x] Issue #69: Admin 댓글 hidden 상태 복원 API 지원 + PR #72 merge 완료
  - `CommentService.restoreComment()`가 `deleted | hidden -> active`를 허용하고, bulk restore도 두 상태를 함께 복원하도록 확장
  - `comment.route.ts` / `comment.schema.ts` / `api-spec.md`에 restore 계약과 `400` 응답 문서를 반영해 Swagger/OpenAPI와 실제 동작을 일치시킴
  - `test/routes/comments.test.ts`에 hidden 단일 복원 및 hidden/deleted 혼합 벌크 복원 통합 테스트 추가
  - Codex review suggestion 1건(restore route `400` 응답 스키마 누락) 반영 후 PR #72 merge

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

- 관련 PR: [PR #72](https://github.com/pyo-sh/pyosh-blog-be/pull/72)
- 관련 이슈: #69
- 검증 메모:
  - `comments.test.ts`에서 hidden 단일 복원과 hidden/deleted 혼합 벌크 복원 케이스 통과 확인
  - 전체 `pnpm test`는 repo 기존 guestbook/stats/health 실패로 green은 아니었음
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
