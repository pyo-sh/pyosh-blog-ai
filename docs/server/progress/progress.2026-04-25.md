# Server Progress - 2026-04-25

## Issue #117 — Guestbook guest email optional 계약 반영 (PR #118 머지)

**Status**: Merged

### What was done

게스트 방명록 생성 요청에서 `guestEmail`을 선택값으로 허용하는 변경이 PR #118로 올라간 상태에서 review 단계부터 파이프라인을 재개했다. Codex review는 동작/테스트 측면에서는 clean이었고, OpenAPI route description이 여전히 게스트가 이름, 이메일, 비밀번호를 모두 보내야 한다고 설명하는 문서 불일치 1건만 제안했다.

제안은 유효하다고 판단해 `src/routes/guestbook/guestbook.route.ts`의 `POST /guestbook` 설명 문자열을 스키마와 일치하도록 수정했다. 이제 게스트는 이름과 비밀번호를 전달해야 하고, 이메일은 선택이라고 명시된다. suggestion-only 리뷰였기 때문에 재리뷰 없이 바로 finalize/merge 경로로 진행했다.

**파일 변경:**
- `src/routes/guestbook/guestbook.route.ts`: guestbook POST OpenAPI 설명을 `guestEmail` 선택 계약에 맞게 수정.

### Review

- codex review 결과 `0 critical / 0 warning / 1 suggestion`.
- 반영 내용: OpenAPI 설명 문구가 optional email 계약과 어긋나던 부분 수정.

### Verification

- `pnpm test` 시도
- 결과: worktree에 `node_modules`가 없어 `vitest: not found`로 실행 불가
- PR #118 squash merge → `main`

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
