# Client Progress - 2026-04-04

## 완료된 작업

### #281 Admin 댓글 상태 전환 UI를 실제 API와 연결 (PR #285 머지)

관리자 댓글 상세 모달과 dashboard 최근 댓글 상세 모달의 상태 전환 UI를 서버 댓글 상태 API와 연결했다. `active / hidden / deleted` 상태 칩을 실제 mutation 흐름으로 바꾸고, 관리자 댓글 목록과 dashboard 최근 댓글 query를 함께 invalidate 하도록 정리했다. 자동 리뷰에서 지적된 선택 상태 누수, stale 에러 메시지, 삭제 확인 모달 우회, in-flight 중복 전환 문제를 순차 반영한 뒤 PR을 병합했다.

**주요 변경 사항:**

- `src/entities/comment/api.ts`, `src/entities/comment/index.ts`, `src/entities/comment/use-admin-comment-status-mutation.ts`
  - `PUT /api/admin/comments/:id/hide` client helper를 추가
  - 상세 모달 상태 칩이 공통으로 사용할 수 있는 댓글 상태 전환 mutation hook을 추가
  - 성공 시 `admin-comments`와 `dashboard recentComments` query를 함께 invalidate 하도록 정리
- `src/widgets/admin-comments/ui/comment-detail-modal.tsx`
  - 읽기 전용 상태 배지를 `정상 / 숨김 / 삭제됨` 상태 칩 UI로 교체
  - pending / error 상태를 모달 안에서 직접 노출
  - `deleted` 전환은 기존 삭제 확인 모달을 거치도록 유지해 cascade 안내와 확인 단계를 보존
- `src/widgets/admin-comments/ui/admin-comments-page.tsx`
  - 상세 모달 상태 전환 성공 시 열린 댓글 데이터를 즉시 동기화
  - 필터에서 사라진 댓글이 bulk selection에 남지 않도록 상태 변경된 댓글 선택을 정리
  - 댓글 전환 에러가 다른 댓글 상세로 누수되지 않도록 modal 대상 변경 시 mutation 상태를 정리
- `src/widgets/dashboard/ui/recent-comments-section.tsx`
  - dashboard 최근 댓글 상세도 동일한 상태 전환 hook을 사용하도록 연결
  - 상태 전환 중에는 댓글을 바꿔 열어도 중복 요청이 나가지 않도록 공통 pending 상태를 그대로 반영
- `src/widgets/admin-post-list/ui/*`
  - 저장소 전체 `pnpm lint` 검증을 복구하기 위해 unrelated prettier/import-order 드리프트를 기계적으로 정리

**리뷰 수정 사항:**

- 상태 변경 후 필터에서 제외된 댓글이 보이지 않는 bulk selection으로 남던 문제 수정
- 댓글을 바꿔 열어도 이전 상태 변경 에러가 남아 보이던 문제 수정
- `deleted` 상태 칩이 삭제 확인 모달을 우회하던 회귀 수정
- 상태 변경 요청이 진행 중일 때 modal 전환으로 중복 mutation을 다시 보낼 수 있던 문제 수정

**검증:**

- `pnpm build`
- `pnpm compile:types`
- `pnpm lint`

**메모:**

- `pnpm lint`는 저장소 기존 warning인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용 1건과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.
- PR `#285`는 자동 리뷰 4라운드를 거쳐 clean 상태로 병합됐다.
