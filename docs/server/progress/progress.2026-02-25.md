# Progress: 2026-02-25

## Completed
- [x] Issue #13: GET /api/admin/posts 쿼리 파라미터 문서화 및 구현
  - `AdminPostListQuerySchema` 신규 생성 (admin 전용 기본값: limit=20, sort=created_at)
  - Admin 라우트에서 기존 `PostListQuerySchema` → `AdminPostListQuerySchema` 교체
  - `api-spec.md`에 GET /api/admin/posts 쿼리 파라미터 스펙 문서화

## Discoveries
- 기존 `PostListQuerySchema`가 Public/Admin 양쪽에서 공유되어 admin 전용 기본값 적용 불가
- `buildPaginatedResponse` 함수 시그니처와 JSDoc 사이 인자 순서 불일치 발견 (별도 이슈로 추적 필요)

## Next Steps
- [ ] PR 리뷰 및 머지
