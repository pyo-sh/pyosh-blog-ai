# Decision 002: Public Shell Height and Admin Login Simplification

## Metadata
- **Date**: 2026-04-10
- **Status**: accepted
- **Related Issue**: -

## Background
Public 페이지 레이아웃에서 헤더 아래 구간이 실제 시각상 비어 보이고, 메인 콘텐츠 높이가 짧을 때 footer가 viewport 하단이 아니라 콘텐츠 바로 아래에 붙는 문제가 있었다.

동시에 `/manage/login` 화면은 장식용 배경 그라데이션과 주변 레이아웃이 로그인 폼 집중도를 떨어뜨리고 있었다. 관리 로그인 화면은 단일 목적 화면이므로, 폼만 정중앙에 두고 나머지 장식을 제거하는 방향이 더 적절하다고 판단했다.

## Option Comparison

### Option A: Public 레이아웃을 세로 flex shell로 재구성하고 admin login을 단순 중앙 정렬 화면으로 축소
- **Pros**: footer를 구조적으로 viewport 하단에 고정할 수 있다.
- **Pros**: 헤더 아래 불필요한 중간 래퍼/여백을 줄여 첫 화면 밀도를 개선할 수 있다.
- **Pros**: `/manage/login`을 폼 중심 화면으로 단순화해 시선 분산 요소를 제거할 수 있다.
- **Pros**: header/footer 높이 변경에 덜 취약하다.
- **Cons**: 퍼블릭 공용 레이아웃 구조를 한 번 정리해야 한다.
- **Cost/Complexity**: medium

### Option B: 현재 구조를 유지하고 퍼블릭 메인 래퍼에 계산식 기반 min-height를 추가
- **Pros**: 변경 범위가 상대적으로 작다.
- **Cons**: header/footer 높이 변화에 취약하다.
- **Cons**: 헤더 아래 빈 느낌을 만드는 구조 자체는 그대로 남는다.
- **Cons**: `/manage/login` 단순화 요구를 함께 해결하지 못한다.
- **Cost/Complexity**: low

## AI Recommendation
> Option A를 권장한다. footer 하단 정렬 문제를 CSS 계산식이 아니라 레이아웃 구조로 해결하는 편이 더 안정적이고, 헤더 아래 밀도 문제와 관리자 로그인 화면 단순화까지 한 번에 정리할 수 있다.

## Final Decision
> Public 영역은 `Header -> flexible content shell -> Footer` 구조의 세로 flex 레이아웃으로 재구성한다. 헤더 아래에서 빈 영역처럼 보이는 불필요한 중간 래퍼는 제거하거나 축소한다. 메인 콘텐츠가 짧아도 footer는 viewport 하단에 위치해야 한다.
>
> `/manage/login`은 배경 장식 레이어와 보라색/기타 그라데이션을 제거하고, `bg-background-1` 단색 배경 위에서 로그인 폼만 화면 정중앙에 배치한다. 로그인 화면에서는 `main > form` 외의 시각적 장식 요소를 두지 않는다.
>
> 계산식 기반 `min-height` 보정 방식인 Option B는 적용하지 않는다.

## Follow-up Actions
- [ ] Public 공용 레이아웃을 세로 flex shell 구조로 재구성한다.
- [ ] 헤더 아래 빈 느낌을 만드는 퍼블릭 중간 래퍼를 제거하거나 축소한다.
- [ ] 메인 콘텐츠 래퍼가 남는 화면 높이를 차지하도록 조정해 footer를 viewport 하단으로 민다.
- [ ] `/manage/login` 레이아웃에서 배경 장식 레이어를 제거한다.
- [ ] `/manage/login`의 로그인 폼을 화면 정가운데에 배치하고 주변 레이아웃을 단순화한다.
