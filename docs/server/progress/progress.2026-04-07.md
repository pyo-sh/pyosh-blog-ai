# Progress: 2026-04-07

## Completed

- [x] Issue #84: 발행 시 summary 자동 생성으로 목록 계약 보장 + PR #85 merge 완료
  - `src/routes/posts/post.service.ts`에 markdown → plain text 200자 summary 추출 로직을 추가하고, `POST /api/admin/posts`에서 `status=published` 저장 시 summary가 비어 있으면 서버가 자동 생성하도록 보강
  - `PATCH /api/admin/posts/:id`에서도 published 저장 기준으로 summary를 재계산하도록 정리해 draft → published 전환과 published 글의 summary clear 후 저장 시 `contentMd` 기반 summary 보장을 회복
  - 같은 publish transition에서 `publishedAt`이 비어 있는 draft 글은 자동으로 현재 시각을 채우도록 보완
  - `test/routes/posts.test.ts`에 published create auto-summary, draft → published auto-summary, published summary regeneration 회귀 테스트를 추가하고 Codex automated review `0 critical / 0 warning / 0 suggestion` clean 결과 확인 후 PR #85 merge

## Notes

- 관련 PR: [PR #85](https://github.com/pyo-sh/pyosh-blog-be/pull/85)
- 관련 이슈: #84
- 검증 메모:
  - `pnpm test --run test/routes/posts.test.ts` 실행 후 `78`개 테스트 통과 확인
  - `pnpm test` 전체 스위트는 변경 범위 밖의 기존 baseline 실패(`test/routes/guestbook.test.ts`, `test/routes/stats.test.ts`, `test/routes/health.test.ts`)를 base branch와 동일하게 재현
