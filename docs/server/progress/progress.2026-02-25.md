# Progress: 2026-02-25

## Completed
- [x] Issue #13: GET /api/admin/posts 쿼리 파라미터 문서화 및 구현
  - `AdminPostListQuerySchema` 신규 생성 (admin 전용 기본값: limit=20, sort=created_at)
  - Admin 라우트에서 기존 `PostListQuerySchema` → `AdminPostListQuerySchema` 교체
  - `api-spec.md`에 GET /api/admin/posts 쿼리 파라미터 스펙 문서화

## Discoveries
- 기존 `PostListQuerySchema`가 Public/Admin 양쪽에서 공유되어 admin 전용 기본값 적용 불가
- `buildPaginatedResponse` 함수 시그니처와 JSDoc 사이 인자 순서 불일치 발견 (별도 이슈로 추적 필요)

- [x] Issue #15: GET /api/assets 에셋 목록 엔드포인트 추가 (PR #21, merged)
  - `assetListItemSchema` (createdAt 포함), `assetListQuerySchema`, `assetListResponseSchema` Zod 스키마 추가
  - `AssetService.getAssetList()` 메서드 구현 — COUNT + 페이지네이션 SELECT, createdAt DESC 정렬
  - `GET /api/assets` 라우트 등록 (Admin preHandler, querystring 검증)
  - `docs/server/api-spec.md`에 엔드포인트 스펙 문서화

## Discoveries
- dev-pipeline 스킬의 Codex/Claude CLI 옵션 오류 발견 및 수정
  - `codex -q` → `codex exec --full-auto` (비대화형 실행)
  - `claude --sandbox -p` → `claude -p --dangerously-skip-permissions` (권한 우회)
- dev-build 스킬에서 PR body 파일 경로(`.workspace/messages/`)가 reference 파일에만 있어 누락 → 메인 SKILL.md에 인라인화
- dev-resolve 스킬에서 worktree 진입 `cd` 명령 누락 → 코드 블록 추가

## Next Steps
- [ ] Client `/dashboard/assets` 페이지에서 GET /api/assets 연동
