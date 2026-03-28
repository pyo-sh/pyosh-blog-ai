# Progress: 2026-03-29

## Completed

- [x] Issue #73: Admin pinned 글 상한(5개) 강제 + pinned count 엔드포인트 추가 + PR #74 merge 완료
  - `GET /api/admin/posts/pinned-count`를 추가해 삭제되지 않은 pinned 글 수를 `{ pinnedCount }`로 반환
  - `PostService`에 pinned 글 상한 5개 검증을 생성, 단일 수정, 단일 복원, 벌크 복원 경로에 적용
  - pinned count를 바꾸는 soft delete, hard delete, restore 전이에 동일한 named lock을 적용해 동시성 경쟁에서도 상한 판단이 일관되도록 정리
  - `test/routes/posts.test.ts`에 pinned count, 6번째 pinned 생성/수정/복원, 벌크 복원 `409` 통합 테스트를 추가하고 review warning 2건을 반영한 뒤 clean review로 PR #74 merge

## Notes

- 관련 PR: [PR #74](https://github.com/pyo-sh/pyosh-blog-be/pull/74)
- 관련 이슈: #73
- 검증 메모:
  - `pnpm exec eslint src/routes/posts/post.service.ts` 통과
  - `pnpm test -- --runInBand test/routes/posts.test.ts -t "pinned 복원으로 6개가 되면 409|action=restore: pinned 복원으로 6개가 되면 409"` 실행 후 `test/routes/posts.test.ts` 74개 통과 확인
