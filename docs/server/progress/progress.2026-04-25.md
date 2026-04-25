# Server Progress - 2026-04-25

## Issue #113 — 휴지통 categoryId NULL 게시글 enrichment 500 복구 (PR #114 머지)

**Status**: Merged

### What was done

카테고리 삭제 시 `action=trash`로 이동된 게시글은 `categoryId`가 `NULL`이 되는데, posts 서비스가 이를 항상 존재하는 카테고리로 가정해 관리자 휴지통 목록과 상세 조회에서 `500`을 내던 버그를 복구했다. 이제 삭제된 uncategorized 게시글은 `categoryId: null`, `category: null`로 정상 응답하며, 카테고리가 없는 글은 단건/벌크 restore에서 `400`으로 명시적으로 차단된다.

**파일 변경:**
- `src/routes/posts/post.service.ts`: 목록/상세 enrichment를 `categoryId === null`에 안전하게 처리하고, 빈 category lookup을 건너뛰며, 단건/벌크 restore에 uncategorized guard 추가.
- `src/routes/posts/post.schema.ts`: post 응답 스키마의 `categoryId`, `category`를 nullable로 조정.
- `test/routes/posts.test.ts`: category `trash` 후 관리자 목록/상세 조회 회귀 테스트와 단건/벌크 restore `400` 검증 추가.

### Review

- codex review 결과 `0 critical / 0 warning / 0 suggestion` clean.

### Verification

- `pnpm test` → `19` files, `286` tests passed
- PR #114 squash merge → `main`
