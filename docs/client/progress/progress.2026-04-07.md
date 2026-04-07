# Client Progress - 2026-04-07

## 완료된 작업

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
