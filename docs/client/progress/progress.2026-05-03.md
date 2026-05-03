# Progress: 2026-05-03

## Completed

- [x] #373 Admin 영역에서 렌더링되는 내부 Next `Link`의 자동 prefetch를 끄도록 `prefetch={false}`를 적용하고 PR #383 머지
- [x] #372 Admin 글 관리 휴지통 탭이 삭제된 글만 조회하도록 `GET /admin/posts` 요청을 `deletedState=deleted` 기반으로 전환하고 PR #382 머지

## Discoveries

- Admin shell/sidebar, dashboard 카드, 글/댓글 목록, preview 링크처럼 인증 상태와 동적 데이터에 의존하는 링크는 Next 기본 viewport/idle prefetch로 클릭 전 RSC payload를 요청할 수 있다.
- 공유 `ErrorContent`도 `context="admin"`이면 admin not-found 액션에서 `/manage` Link를 렌더링하므로 admin 컨텍스트일 때 prefetch를 끄는 보정이 필요하다.
- 서버의 legacy `includeDeleted=true`는 삭제 글 전용 조회가 아니라 active + deleted 전체 조회로 해석된다.
- 삭제 상태를 명시하려면 `deletedState=active|deleted|all`을 사용해야 하며, 휴지통 탭은 `deletedState=deleted`를 보내야 페이지네이션 meta와 목록 row가 함께 맞는다.
- Storybook/MSW가 `includeDeleted=true`를 삭제 글 전용으로 흉내 내면 실제 서버 의미와 달라져 휴지통 회귀를 가리지 못한다.

## Issues & Resolutions

- **Issue**: `/manage/posts` 진입 직후 사이드바, dashboard, preview 등 사용자가 클릭하지 않은 admin/public route의 RSC payload가 자동 prefetch될 수 있음
- **Resolution**: admin 영역에서 렌더링되는 scoped `Link`에 `prefetch={false}`를 추가해 클릭 이동은 유지하되 자동 사전 요청을 차단
- **Issue**: Admin not-found/error action의 공유 `ErrorContent` Link가 `/manage`를 기본 prefetch할 수 있음
- **Resolution**: `ErrorContent`에서 `context === "admin"`인 link action에만 `prefetch={false}`를 적용하고 public context 기본 동작은 유지
- **Issue**: `/manage/posts` 휴지통 탭이 `includeDeleted=true`를 보내 정상 발행 글까지 휴지통 목록에 포함될 수 있음
- **Resolution**: `FetchAdminPostsParams`에 `deletedState`를 추가하고 휴지통 탭에서는 `deletedState: "deleted"`를 전달하도록 변경. active 탭은 서버 기본 active-only 조회를 유지
- **Issue**: Storybook/MSW post list handler가 `includeDeleted=true`를 deleted-only로 처리해 실제 API 동작과 불일치
- **Resolution**: MSW handler에서 `includeDeleted=true`는 all 조회로, `deletedState=deleted`는 deleted-only 조회로 분리

## Verification

- #373: `pnpm compile:types`
- #373: `pnpm lint` (기존 warning 2건 유지)
- #373: `pnpm build`
- #373: 자동 리뷰 suggestion 1건 반영 후 clean, PR #383 머지
- `pnpm compile:types`
- `pnpm lint` (기존 warning 2건 유지)
- `pnpm build`
- 자동 리뷰 clean, PR #382 머지
