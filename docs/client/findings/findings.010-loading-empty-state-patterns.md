# findings.010 - 로딩/빈 상태 컴포넌트 설계 패턴

**Date:** 2026-03-27
**Issue:** #169 [F-13]
**Tags:** #skeleton #spinner #empty-state #accessibility #aria

## 1. Spinner를 버튼 내부에서 사용할 때 `role="status"` 제거

버튼 안에 `<Spinner>` + 텍스트를 함께 둘 때, Spinner에 `role="status"` + `aria-label`을 붙이면 스크린 리더가 버튼 label과 live region을 각각 별도로 읽어 이중 공지(double announcement)가 발생한다.

- **해결**: Spinner는 `aria-hidden="true"` SVG만 렌더링하고 `role="status"` 생략. 버튼 자체의 텍스트("로그인 중", "삭제 중")가 상태를 충분히 전달한다.
- **적용 대상**: 버튼 안에 인라인으로 삽입되는 모든 Spinner 사용처

## 2. Skeleton `circle` variant 기본 너비

Skeleton에 `variant="circle"`을 사용할 때 너비를 명시하지 않으면 컨테이너 전체 너비를 차지하는 pill 형태로 렌더링된다. `variantDefaults.circle`에 `width: "2rem"` 기본값을 추가하고, style 계산 시 `width ?? defaults.width ?? "100%"` 우선순위를 적용하여 해결한다.

## 3. EmptyState의 `variant` prop 패턴

관리자(Admin) 페이지와 공개(Public) 페이지는 EmptyState의 시각 스타일이 다르다.

| variant | 배경 | 패딩 | 타이포 | 사용처 |
|---------|------|------|--------|--------|
| `default` | `bg-background-1` | `px-6 py-12` | `text-sm` | 관리자 페이지 (대시보드) |
| `page` | `bg-background-2` | `p-8 md:p-10` | `text-body-md` | 공개 페이지 (tags, search, guestbook 등) |

두 스타일을 하나의 컴포넌트로 통합하되 `variant` prop으로 분기하는 것이 `className` override만 제공하는 것보다 사용 실수가 적다.

## 4. Grid 레이아웃에서 Skeleton `repeat` prop 미사용

Skeleton의 `repeat` prop은 반복 항목을 `<div>` wrapper로 감싸므로, CSS grid의 직계 자식 조건이 필요한 테이블 헤더/행 스켈레톤에서는 사용할 수 없다.

- **해결**: `Array.from({ length: N }).map(() => <Skeleton ... />)`으로 직접 반복

## 5. 로컬 스켈레톤 정의를 Skeleton 컴포넌트로 교체할 때 `animate-pulse` 중복 제거

기존 로딩 파일들은 카드 컨테이너에 `animate-pulse`를 걸고, 내부 div에도 `bg-background-3`로 색을 적용하는 패턴이었다. Skeleton 컴포넌트 자체가 `animate-pulse`를 담당하므로 외부 컨테이너의 `animate-pulse`는 제거해야 한다. 중복 적용 시 애니메이션이 이중으로 걸려 시각적으로 어색할 수 있다.
