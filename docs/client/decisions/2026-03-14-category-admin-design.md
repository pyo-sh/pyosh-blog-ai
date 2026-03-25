# Category Admin Feature Design

## Metadata
- **Date**: 2026-03-14
- **Status**: accepted
- **Related Issue**: client #57

## Background

Client admin 영역에 `/dashboard/categories` 페이지가 아직 없고, 카테고리 관리 UX도 비어 있다. 이번 작업은 카테고리 트리를 시각화하고, 추가/수정 모달과 삭제 확인 흐름을 제공해 관리자 페이지에서 기본 CRUD를 수행할 수 있게 만드는 것이다.

관련 선행 작업으로 `#62`에서 category admin API functions가 준비되어 있으며, 이번 이슈는 그 API를 TanStack Query 기반 UI에 연결하는 범위다.

## Option comparison

| Option | Pros | Cons |
|--------|------|------|
| A. `app` 페이지에서 query/mutation/modal state를 직접 관리 | 구현이 빠름 | `src/app/` routing-only 규칙 위반 가능성이 큼 |
| B. `features/category-manager`에 상태와 UI를 모으고 `app`은 thin entry로 유지 | FSD 경계가 명확함, 재사용/테스트에 유리 | feature 루트 컴포넌트를 하나 더 만들어야 함 |
| C. `widgets/category-admin-page`를 추가해 page와 feature 사이에 한 단계 더 둠 | 장기 확장성은 좋음 | 현재 스코프 대비 구조가 과함 |

## Final decision

**Option B**를 채택한다.

- `src/app/dashboard/categories/page.tsx`는 routing entry만 담당한다.
- 실제 query/mutation/modal orchestration은 `src/features/category-manager`에 둔다.
- `CategoryTree`와 `CategoryFormModal`은 feature 내부 UI 컴포넌트로 구현한다.
- 카테고리 목록은 `fetchCategoriesAdmin()`을 TanStack Query로 읽고, create/update/delete 후 invalidate로 갱신한다.
- 삭제는 자식 카테고리가 있으면 서버 호출 전에 차단하고 안내만 표시한다.
- 수정 모드에서 부모 선택 옵션은 현재 노드와 descendant를 제외해 순환 구조를 막는다.

## Interaction rules

- 트리는 depth를 시각적으로 드러내고 각 행에 수정/삭제 액션을 둔다.
- hidden 카테고리는 badge나 보조 텍스트로 상태를 명시한다.
- 추가/수정은 공용 모달로 처리하고, 수정 시 현재 값으로 초기화한다.
- 삭제는 자식이 없을 때만 확인 후 실행한다.

## Verification

- `pnpm lint`
- `pnpm build`
- `pnpm compile:types`
