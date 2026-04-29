# Server Progress - 2026-04-29

## Issue #119 - 카테고리 일괄 삭제 API (PR #120 머지)

**Status**: Merged

### What was done

관리자 카테고리 화면의 일괄 선택 삭제를 지원하기 위해 `DELETE /categories/bulk` API를 추가했다. 요청 본문은 `{ ids, action, moveTo }` 형태이며, 기존 단건 삭제의 `move`/`trash` 정책을 유지하면서 여러 카테고리를 단일 트랜잭션으로 처리한다.

입력 검증은 빈 `ids`, 100개 초과, 중복 ID, `moveTo` 누락을 400으로 막도록 스키마와 서비스 양쪽에 방어를 두었다. 서비스 레이어에서는 선택된 카테고리 전체 존재 여부를 확인하고, 하위 카테고리가 있는 대상은 409로 거부하며, `moveTo`가 삭제 대상에 포함되거나 존재하지 않는 경우를 차단한다. `trash`는 미삭제 게시글을 soft delete하고 `categoryId`를 null로 정리하며, `move`는 미삭제 게시글만 대상 카테고리로 이동하고 이미 soft-deleted 된 게시글은 `categoryId`를 null로 정리한다.

**파일 변경:**
- `src/routes/categories/category.schema.ts`: 벌크 삭제 요청 스키마 추가.
- `src/routes/categories/category.route.ts`: `DELETE /categories/bulk`를 `/:id`보다 앞에 등록하고 Admin 인증/CSRF 보호 적용.
- `src/routes/categories/category.service.ts`: 트랜잭션 기반 `deleteCategories` 구현.
- `test/routes/categories.test.ts`: 인증/CSRF route hook, 검증 실패, 하위 카테고리 실패, move/trash 성공 DB 상태, `/bulk` 정적 경로 매칭 회귀 테스트 추가.

### Review

- codex review 결과 `0 critical / 0 warning / 0 suggestion` clean.

### Verification

- `pnpm compile:types`
- `pnpm lint`
- `pnpm test test/routes/categories.test.ts` -> `42` tests passed
- `pnpm test` -> `19` files, `298` tests passed
- PR #120 squash merge -> `main`
