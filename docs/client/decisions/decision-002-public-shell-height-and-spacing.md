# Decision 002: Public Shell Height and Spacing

## Metadata
- **Date**: 2026-04-10
- **Status**: accepted
- **Related Issue**: -

## Background
Public 페이지 레이아웃에서 헤더 아래 구간이 실제 시각상 비어 보이고, 메인 콘텐츠 높이가 짧을 때 footer가 viewport 하단이 아니라 콘텐츠 바로 아래에 붙는 문제가 있었다.

이 문제는 개별 페이지 높이 보정보다 공용 shell 구조에서 해결하는 편이 더 안정적이다.

## Option Comparison

### Option A: Public 레이아웃을 세로 flex shell로 재구성
- **Pros**: footer를 구조적으로 viewport 하단에 고정할 수 있다.
- **Pros**: 헤더 아래 불필요한 중간 래퍼/여백을 줄여 첫 화면 밀도를 개선할 수 있다.
- **Pros**: header/footer 높이 변경에 덜 취약하다.
- **Cons**: 퍼블릭 공용 레이아웃 구조를 한 번 정리해야 한다.
- **Cost/Complexity**: medium

### Option B: 현재 구조를 유지하고 퍼블릭 메인 래퍼에 계산식 기반 min-height를 추가
- **Pros**: 변경 범위가 상대적으로 작다.
- **Cons**: header/footer 높이 변화에 취약하다.
- **Cons**: 헤더 아래 빈 느낌을 만드는 구조 자체는 그대로 남는다.
- **Cost/Complexity**: low

## AI Recommendation
> Option A를 권장한다. footer 하단 정렬 문제를 CSS 계산식이 아니라 레이아웃 구조로 해결하는 편이 더 안정적이고, 헤더 아래 밀도 문제도 함께 정리할 수 있다.

## Final Decision
> Public 영역은 `Header -> flexible content shell -> Footer` 구조의 세로 flex 레이아웃으로 재구성한다.
>
> 헤더 아래에서 빈 영역처럼 보이는 불필요한 중간 래퍼는 제거하거나 축소한다.
>
> 메인 콘텐츠가 짧아도 footer는 viewport 하단에 위치해야 한다.
>
> 계산식 기반 `min-height` 보정 방식은 적용하지 않는다.

## Follow-up Actions
- [ ] Public 공용 레이아웃을 세로 flex shell 구조로 재구성한다.
- [ ] 헤더 아래 빈 느낌을 만드는 퍼블릭 중간 래퍼를 제거하거나 축소한다.
- [ ] 메인 콘텐츠 래퍼가 남는 화면 높이를 차지하도록 조정해 footer를 viewport 하단으로 민다.
