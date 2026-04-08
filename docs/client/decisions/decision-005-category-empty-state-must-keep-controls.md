# Decision 005: Category Empty State Must Keep Management Controls

## Metadata
- **Date**: 2026-04-10
- **Status**: accepted
- **Related Issue**: -

## Background
카테고리 페이지에서 카테고리가 하나도 없을 때 control box가 함께 사라져, 사용자가 새 카테고리를 생성하거나 관리 화면으로 진입할 수 없는 문제가 있다.

빈 상태는 안내만 보여주는 화면이 아니라, 다음 행동을 시작할 수 있어야 하는 상태다. 특히 카테고리처럼 초기 데이터가 비어 있을 수 있는 도메인에서는 생성 액션이 비어 있는 순간에도 항상 접근 가능해야 한다.

## Option Comparison

### Option A: 빈 상태와 무관하게 control box를 항상 렌더링
- **Pros**: 카테고리가 0개여도 즉시 생성/관리 액션을 제공할 수 있다.
- **Pros**: 사용자가 막히지 않고 첫 카테고리 생성 흐름을 시작할 수 있다.
- **Pros**: 상태별 분기가 줄어들어 UX가 일관된다.
- **Cons**: empty state 레이아웃과 control box의 배치를 다시 정리해야 할 수 있다.
- **Cost/Complexity**: low

### Option B: 빈 상태에서는 안내 문구만 보여주고 별도 링크나 CTA로 우회 제공
- **Pros**: 기존 control box 구조를 크게 바꾸지 않아도 된다.
- **Cons**: 관리 기능 접근 경로가 분리되어 UX가 일관되지 않다.
- **Cons**: 사용자가 control box가 있는 일반 상태와 다른 인터랙션을 배워야 한다.
- **Cost/Complexity**: low

## AI Recommendation
> Option A를 권장한다. 빈 상태는 생성 액션이 가장 필요한 순간이므로, control box를 숨기지 않고 항상 같은 위치에서 제공하는 편이 더 직관적이다.

## Final Decision
> 카테고리 페이지에서는 카테고리 데이터 유무와 무관하게 control box를 항상 노출한다. 카테고리가 0개일 때도 사용자는 동일한 화면 안에서 새 카테고리 생성 또는 관리 액션을 바로 실행할 수 있어야 한다.
>
> empty state는 control box를 대체하는 것이 아니라 보완하는 안내 영역으로 취급한다. 즉, 빈 상태 메시지가 있더라도 생성/관리 액션은 별도로 유지한다.

## Follow-up Actions
- [ ] 카테고리 페이지의 empty state 분기에서 control box가 제거되지 않도록 구조를 조정한다.
- [ ] 카테고리 0개 상태에서도 새 카테고리 생성 액션을 바로 실행할 수 있게 한다.
- [ ] 필요하면 empty state와 control box의 시각적 우선순위를 재정렬한다.
