# Client Progress - 2026-04-20

## 완료된 작업

### #314 발행된 게시글 상세 페이지 404 및 slug 무결성 문제 - 1차 완화 (PR #315 머지)

운영 환경에서 발행된 게시글이 public 목록과 `api.pyosh.com/posts/{slug}`에서는 정상 조회되는데, Next.js public 상세 페이지에서는 `NEXT_NOT_FOUND`로 렌더되던 문제를 1차 완화했다. 원인 후보를 분리한 결과 상세 페이지는 게시글 본문 조회 외에도 댓글 preload 실패를 전체 `notFound()`로 전파할 수 있는 구조였고, 특히 `src/app/(public)/posts/[slug]/page.tsx`에서 댓글 요청 404를 재throw한 뒤 페이지 단위 catch가 이를 다시 `notFound()`로 바꾸고 있었다. 이번 변경에서는 게시글 조회만 404를 결정하도록 범위를 좁히고, 댓글 preload 실패는 댓글 섹션 에러 상태로만 처리하도록 조정했다. PR `#315`는 동기 `codex` 리뷰 clean 판정 후 병합됐다.

**주요 변경 사항:**

- `src/app/(public)/posts/[slug]/page.tsx`
  - 페이지 전체를 감싸던 broad `try/catch`를 제거해 post lookup 외 404가 상세 페이지 전체를 `notFound()`로 바꾸지 않도록 정리
  - `fetchComments(post.id, ...)` 실패 시 404 포함 모든 에러를 댓글 섹션 로딩 실패로만 처리하고, 사용자 메시지를 노출하도록 완화
  - 결과적으로 게시글 상세 페이지의 404 결정권을 `getPostDetail()` 경로로 한정

**검증:**

- `pnpm install --frozen-lockfile`
- `pnpm compile:types`
- `pnpm lint` *(저장소 기존 warning 2건 유지)*
- `pnpm build`

**메모:**

- `pnpm lint`는 저장소 기존 warning인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용 1건과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.
- 이번 수정은 상세 페이지 404의 1차 완화다. 운영 API 응답에서 `category.slug === ""`, `tag.slug === ""`가 확인돼 slug 데이터 무결성 문제는 별도 후속 작업이 필요하다.
- 게시글 URL 구조 자체는 여전히 slug-only에 의존하므로, 장기적으로는 stable id + display slug 구조 전환 검토가 남아 있다.
