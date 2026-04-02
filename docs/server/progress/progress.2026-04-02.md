# Progress: 2026-04-02

## Completed

- [x] Issue #75: Admin 댓글 hidden 상태 전환 API 추가 + PR #76 merge 완료
  - `PUT /api/admin/comments/:id/hide`를 추가하고, `DELETE /api/admin/comments/bulk`에 `hide` 액션을 확장해 관리자 댓글을 `active -> hidden`으로 전환할 수 있게 함
  - `CommentService`에 hide 전이 규칙을 추가하고, hidden 루트 댓글 아래의 active 답글이 public 목록/메타를 오염시키지 않도록 public comment visibility/count 로직을 정리
  - `PostService`의 post list/detail `commentCount`, `sort=commentCount`, `filter=comment` 집계를 public comment visibility 규칙과 동일하게 맞춰 hidden 댓글로 인한 aggregate 불일치를 제거
  - 새 hide 경로(단건/벌크)에 CSRF 보호를 적용하고, `test/routes/comments.test.ts`와 `test/routes/posts.test.ts`에 hide/aggregate 회귀 테스트를 추가
  - Codex review warning 5건(고아 답글, JS count 회귀, 단건 hide CSRF, 벌크 hide CSRF, post comment aggregate drift)을 순차 반영한 뒤 clean review로 PR #76 merge

## Notes

- 관련 PR: [PR #76](https://github.com/pyo-sh/pyosh-blog-be/pull/76)
- 관련 이슈: #75
- 검증 메모:
  - `pnpm exec vitest run test/routes/posts.test.ts test/routes/comments.test.ts` 실행 후 `112`개 테스트 통과 확인
