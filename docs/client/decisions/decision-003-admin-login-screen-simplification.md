# Decision 003: Admin Login Screen Simplification

## Metadata
- **Date**: 2026-04-10
- **Status**: accepted
- **Related Issue**: -

## Background
`/manage/login` 화면은 장식용 배경 그라데이션과 주변 레이아웃이 로그인 폼 집중도를 떨어뜨리고 있었다. 관리 로그인 화면은 단일 목적 화면이므로, 폼만 정중앙에 두고 나머지 장식을 제거하는 방향이 더 적절하다.

## Option Comparison

### Option A: 로그인 폼만 남기고 화면을 단순 중앙 정렬 구조로 축소
- **Pros**: 로그인 목적이 분명해지고 시선 분산 요소가 사라진다.
- **Pros**: 배경과 주변 레이아웃을 단순화해 유지보수가 쉬워진다.
- **Pros**: admin entry screen의 밀도가 안정적이다.
- **Cons**: 기존 장식성 레이아웃은 제거된다.
- **Cost/Complexity**: low

### Option B: 기존 장식을 유지한 채 일부만 조정
- **Pros**: 변경량이 적다.
- **Cons**: 폼 집중도 저하 원인이 남는다.
- **Cons**: 향후 또 세부 조정을 반복할 가능성이 높다.
- **Cost/Complexity**: low

## AI Recommendation
> Option A를 권장한다. `/manage/login`은 단일 액션 화면이므로 장식보다 명확성이 우선이다.

## Final Decision
> `/manage/login`은 배경 장식 레이어와 보라색/기타 그라데이션을 제거하고, `bg-background-1` 단색 배경 위에서 로그인 폼만 화면 정중앙에 배치한다.
>
> 로그인 화면에서는 `main > form` 외의 시각적 장식 요소를 두지 않는다.

## Follow-up Actions
- [ ] `/manage/login` 레이아웃에서 배경 장식 레이어를 제거한다.
- [ ] `/manage/login`의 로그인 폼을 화면 정가운데에 배치한다.
- [ ] 로그인 화면 주변 레이아웃을 단순화한다.
