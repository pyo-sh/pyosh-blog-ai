# Progress: 2026-04-06

## Completed

- [x] Issue #79: Category/Asset mutation route CSRF 누락 수정 + PR #82 merge 완료
  - `src/routes/categories/category.route.ts`의 `POST /api/categories`, `PATCH /api/categories/tree`, `PATCH /api/categories/:id`, `DELETE /api/categories/:id`에 `fastify.csrfProtection`을 명시적으로 연결해 `/api/admin/*` 바깥의 관리자 mutation route도 문서와 동일한 CSRF 보호를 받도록 정리
  - `src/routes/assets/asset.route.ts`의 `DELETE /api/assets/:id`, `DELETE /api/assets/bulk`에 동일한 CSRF hook을 추가해 upload route와 보호 수준을 맞춤
  - `test/routes/categories.test.ts`, `test/routes/assets.test.ts`에 `app.printRoutes({ includeHooks: true })` 기반 회귀 테스트를 추가해 test 환경의 no-op CSRF 플러그인 아래에서도 route-level hook 등록 누락을 검출하도록 보강
  - Codex automated review 결과 `0 critical / 0 warning / 0 suggestion`으로 clean review 확인 후 PR #82 merge

## Notes

- 관련 PR: [PR #82](https://github.com/pyo-sh/pyosh-blog-be/pull/82)
- 관련 이슈: #79
- 검증 메모:
  - `NODE_ENV=test ./node_modules/.bin/vitest run test/routes/categories.test.ts test/routes/assets.test.ts` 실행 후 `47`개 테스트 통과 확인
  - `pnpm test` 전체 스위트는 변경 범위 밖의 기존 baseline 실패(`test/routes/guestbook.test.ts`, `test/routes/stats.test.ts`, `test/routes/health.test.ts`)를 동일하게 재현
