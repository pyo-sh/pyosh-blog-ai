# Progress: 2026-04-29

## Completed

- [x] #360 관리자 카테고리 일괄 선택 모드에 삭제 액션을 추가하고 PR #362 머지
- [x] #359 관리자 카테고리 배치 편집에서 3-depth 하위 노드를 상위 부모로 이동할 때 중간 노드가 working tree UI에서 사라지는 문제를 수정하고 PR #361 머지

## Discoveries

- 카테고리 벌크 삭제 서버 계약은 `DELETE /categories/bulk` + JSON body `{ ids, action, moveTo? }`이며, 단건 삭제와 동일한 move/trash 정책을 클라이언트에서 먼저 안내해야 한다.
- `removeCategory()`는 대상의 직접 부모 `children` 배열을 `splice()`로 이미 갱신하므로, 재귀 복귀 중 `result.tree`를 상위 조상의 `children`에 다시 대입하면 조상 트리 구조가 손상된다.

## Issues & Resolutions

- **Issue**: 일괄 선택 하단 액션 바에 선택한 카테고리를 한 번에 삭제하는 액션이 없고, 글이 있거나 하위 카테고리가 있는 선택 조합을 안전하게 처리할 UI가 없음
- **Resolution**: `deleteCategories(ids, options)` API helper를 추가하고, 선택 모드 삭제 버튼 + 벌크 삭제 모달을 연결해 하위 카테고리 포함 시 차단, 글 포함 시 move/trash 선택, 이동 대상에서 삭제 대상을 제외하도록 구현
- **Issue**: `테스트1 > 테스트2 > 테스트3`에서 `테스트3`을 `테스트1`의 자식으로 이동하면 재귀 복귀 중 `테스트1.children`이 `테스트2.children` 결과로 덮여 `테스트2`가 UI에서 누락됨
- **Resolution**: `removeCategory()` 반환값을 제거된 카테고리만 담도록 축소하고, 상위 재귀 호출에서 직접 부모의 child list를 조상에게 재대입하지 않도록 정리

## Verification

- #360: `pnpm compile:types`, `pnpm lint` (기존 warning 2건 유지), `pnpm build`, 자동 리뷰 clean
- `node --experimental-strip-types` one-off fixture: 3-depth inside 이동, cross-level before 이동, 동일 부모 before 이동, `calculateTreeChanges()` 결과 확인
- `pnpm compile:types`
- `pnpm lint` (기존 warning 2건 유지)
- `pnpm build`
