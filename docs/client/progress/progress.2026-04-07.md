# Client Progress - 2026-04-07

## 완료된 작업

### #289 Admin auth client username 계약 전환 (PR #294 머지)

관리자 로그인 클라이언트를 현재 서버 응답 구조에 맞게 정리했다. `auth` entity의 admin 타입에서 legacy `displayName`을 제거하고 `POST /api/auth/admin/login` 응답을 `{ admin }` 래퍼에서 안전하게 unwrap하도록 수정했다. 로그인 폼에서는 `username` 값을 trim 없이 그대로 전송하도록 바꾸고, 라벨/placeholder/helper copy를 이메일이 아닌 사용자명 기준으로 정리했다. 1차 자동 리뷰에서 클라이언트가 서버보다 더 엄격한 username 제약과 `autocomplete="off"`를 도입한 점이 경고로 잡혀, 브라우저 단의 과도한 길이/pattern 제한을 제거하고 `autoComplete="username"`을 복원한 뒤 재리뷰 clean 상태로 PR을 병합했다.

**주요 변경 사항:**

- `src/entities/auth/model.ts`
  - admin 로그인 응답 타입을 `id/username/createdAt/updatedAt/lastLoginAt` 구조로 정리
  - legacy `displayName` 필드를 제거하고 `/api/auth/me`의 admin shape와 일치시킴
- `src/entities/auth/api.ts`
  - `clientFetch<{ admin: AdminUser }>()`로 로그인 응답을 받고 `response.admin`을 반환하도록 수정
- `src/features/admin-login/ui/login-form.tsx`
  - `username.trim()` 제거로 입력값을 그대로 전송
  - 라벨/placeholder/helper를 사용자명 기준으로 정리
  - `autoComplete="username"` 유지, `autoCapitalize="none"`/`autoCorrect="off"`/`spellCheck={false}` 적용

**검증:**

- `pnpm compile:types`
- `pnpm lint`
- `pnpm build` *(환경 이슈로 실패)*

**메모:**

- `pnpm lint`는 저장소 기존 warning인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용 1건과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.
- `pnpm build`는 이번 변경과 무관하게 원본 `client` 저장소와 issue worktree 모두에서 `lightningcss.linux-arm64-gnu.node` 누락으로 실패했다.
- PR `#294`는 동기 `codex` 리뷰 2라운드 후 clean 판정으로 병합됐다.

### #287 Admin 방명록 hide/restore HTTP method 불일치 수정 (PR #291 머지)

관리자 방명록 `hide/restore` helper가 삭제 helper를 재사용하면서 `DELETE`로 요청하던 문제를 서버 계약에 맞게 정리했다. `guestbook` entity API에서 삭제 계열과 상태 전환 계열 helper의 책임을 분리해 단건/벌크 `hide` 및 `restore` 요청이 모두 `PATCH`를 사용하도록 수정했고, 동기 `codex` 리뷰 clean 상태까지 확인한 뒤 PR을 병합했다.

**주요 변경 사항:**

- `src/entities/guestbook/api.ts`
  - `adminPatchGuestbookEntry()`가 삭제 helper 위임 대신 `PATCH /api/admin/guestbook/:id?action=...`를 직접 호출하도록 수정
  - `adminBulkPatchGuestbookEntries()`가 `PATCH /api/admin/guestbook/bulk`를 사용하도록 수정
  - 삭제 helper는 `soft_delete`/`hard_delete` 액션만 받도록 타입을 좁혀 patch/delete 의미를 분리

**검증:**

- `pnpm compile:types`
- `pnpm lint`
- `pnpm build`

**메모:**

- `pnpm lint`는 저장소 기존 warning인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용 1건과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.
- `pnpm build`는 이번 변경과 무관하게 원본 `client` 저장소와 issue worktree 모두에서 `lightningcss.linux-arm64-gnu.node` 누락으로 실패했다.
- PR `#291`은 동기 `codex` 리뷰에서 clean 판정 후 바로 병합됐다.
