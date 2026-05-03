# Progress: 2026-05-03

## Completed

- [x] #372 Admin 글 관리 휴지통 탭이 삭제된 글만 조회하도록 `GET /admin/posts` 요청을 `deletedState=deleted` 기반으로 전환하고 PR #382 머지

## Discoveries

- 서버의 legacy `includeDeleted=true`는 삭제 글 전용 조회가 아니라 active + deleted 전체 조회로 해석된다.
- 삭제 상태를 명시하려면 `deletedState=active|deleted|all`을 사용해야 하며, 휴지통 탭은 `deletedState=deleted`를 보내야 페이지네이션 meta와 목록 row가 함께 맞는다.
- Storybook/MSW가 `includeDeleted=true`를 삭제 글 전용으로 흉내 내면 실제 서버 의미와 달라져 휴지통 회귀를 가리지 못한다.

## Issues & Resolutions

- **Issue**: `/manage/posts` 휴지통 탭이 `includeDeleted=true`를 보내 정상 발행 글까지 휴지통 목록에 포함될 수 있음
- **Resolution**: `FetchAdminPostsParams`에 `deletedState`를 추가하고 휴지통 탭에서는 `deletedState: "deleted"`를 전달하도록 변경. active 탭은 서버 기본 active-only 조회를 유지
- **Issue**: Storybook/MSW post list handler가 `includeDeleted=true`를 deleted-only로 처리해 실제 API 동작과 불일치
- **Resolution**: MSW handler에서 `includeDeleted=true`는 all 조회로, `deletedState=deleted`는 deleted-only 조회로 분리

## Verification

- `pnpm compile:types`
- `pnpm lint` (기존 warning 2건 유지)
- `pnpm build`
- 자동 리뷰 clean, PR #382 머지
