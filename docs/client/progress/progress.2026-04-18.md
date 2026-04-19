# Client Progress - 2026-04-18

## 완료된 작업

### #310 Client API 경로에서 /api prefix 제거 (PR #311 머지)

서버의 `/api` prefix 제거에 맞춰 client 전역의 API 호출 경로를 루트 기준 경로로 정렬했다. 공개/관리자 API helper, CSRF 토큰 조회, 조회수 기록, middleware 인증 확인, Storybook MSW handler를 함께 업데이트해 런타임 호출과 스토리북 mock이 같은 계약을 보도록 맞췄다. 자동 리뷰는 clean으로 종료됐고 PR `#311`이 병합됐다.

**주요 변경 사항:**

- `src/entities/{auth,asset,category,comment,guestbook,post,stat,tag}/api.ts`
  - public/admin endpoint 경로를 `/api/...` 에서 `/...` 로 일괄 변경
  - asset upload XHR 경로와 post/comment/guestbook/stat/auth helper를 새 서버 경로에 맞춤
- `src/shared/api/csrf.ts`, `src/shared/hooks/use-view-count.ts`, `src/shared/hooks/use-site-view-count.ts`, `src/middleware.ts`
  - CSRF token 조회, 조회수 mutation, middleware의 `auth/me` 인증 체크 경로를 새 계약으로 정렬
- `stories/**/*`
  - Storybook MSW handler와 story별 mock URL을 새 경로로 변경
  - category/assets mock 일부를 실제 client 응답 shape에 맞게 수정

**검증:**

- `pnpm compile:types`
- `pnpm lint`
- `pnpm build` 실행 시도

**메모:**

- `pnpm lint`는 저장소 기존 warning인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용 1건과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.
- `pnpm build`는 코드 오류가 아니라 현재 환경의 `lightningcss.linux-arm64-gnu.node` 네이티브 바이너리 누락으로 실패했다.
- 자동 리뷰 결과는 Critical/Warning/Suggestion 모두 0건이었다.
