# Client Progress - 2026-04-06

## 완료된 작업

### #286 Admin 로그아웃 CSRF 계약 불일치 수정 (PR #290 머지)

관리자 로그아웃 helper가 CSRF 토큰 없이 `POST /api/auth/admin/logout`를 호출하던 경로를 서버 계약에 맞게 정리했다. `logout()`을 일반 fetch 경로에서 CSRF-aware mutation helper로 바꿔 기존 UI 호출부는 그대로 유지하면서 요청 헤더에 CSRF 토큰이 포함되도록 수정했고, 자동 리뷰 clean 상태까지 확인한 뒤 PR을 병합했다.

**주요 변경 사항:**

- `src/entities/auth/api.ts`
  - `logout()`이 `clientFetch` 직접 호출 대신 `clientMutate`를 사용하도록 변경
  - 관리자 로그아웃 POST 요청이 shared CSRF 토큰 주입 경로를 타도록 정리

**검증:**

- `pnpm install --frozen-lockfile`
- `pnpm compile:types`
- `pnpm lint`
- `pnpm build`

**메모:**

- `pnpm lint`는 저장소 기존 warning인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용 1건과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.
- PR `#290`은 동기 `codex` 리뷰에서 clean 판정 후 바로 병합됐다.
