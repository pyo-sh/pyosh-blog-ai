# [F-13] 로딩/빈 상태

> 페이지 전환, 데이터 페칭, 액션 실행 시 로딩 상태와 데이터가 없을 때 빈 상태를 표시하는 공통 시스템.

## SPEC 참조

- `docs/client/specs/loading-empty-states.md`

## 와이어프레임

- `docs/client/designs/public/loading-empty-states.html` - 로딩 스켈레톤 상태
- `docs/client/designs/public/loading-empty-states-empty.html` - 빈 상태 UI
- 공통 디자인 시스템: `docs/client/designs/DESIGN_SYSTEM.md`

## 상세 설계

### 로딩 상태 분류

| 유형 | 트리거 | UI |
|---|---|---|
| 페이지 전환 | Next.js 라우트 이동 | `loading.tsx` Skeleton |
| 초기 데이터 로딩 | React Query `isPending` | 해당 영역 Skeleton |
| 리페칭 | React Query `isFetching` | 인라인 텍스트 ("목록을 새로 불러오는 중...") |
| 액션 실행 | 버튼 클릭 (삭제, 저장 등) | 버튼 내 Spinner + 버튼 비활성화 |

### Skeleton 컴포넌트

#### Props

| Prop | 타입 | 설명 |
|---|---|---|
| `variant` | `"text"` \| `"circle"` \| `"rect"` | 형태. 기본값 `"text"` |
| `width` | `string` | 너비. 기본값 `"100%"` |
| `height` | `string` | 높이. `variant`별 기본값 적용 |
| `repeat` | `number` | 반복 횟수. 기본값 `1` |

#### 스타일

- `animate-pulse` 애니메이션
- `bg-background-4` 배경색 (기존 패턴 유지)
- `rounded-full` (text), `rounded-full` (circle), `rounded-lg` (rect)

#### 사용 예시

```tsx
// 기존: 로컬 정의
function TableSkeleton() {
  return (
    <div className="h-4 animate-pulse rounded-full bg-background-4" />
  );
}

// 변경: 공유 컴포넌트
import { Skeleton } from "@/shared/ui";

function TableSkeleton() {
  return <Skeleton variant="text" repeat={5} />;
}
```

#### 교체 대상

| 현재 위치 | 로컬 정의 |
|---|---|
| `app/loading.tsx` | 인라인 Skeleton |
| `app/manage/loading.tsx` | 인라인 Skeleton |
| `app/manage/posts/page.tsx` | `TableSkeleton()` |
| `features/category-manager` | `TreeSkeleton()` |
| `features/guestbook-manager` | `TableSkeleton()` |
| `widgets/admin-comments` | `TableSkeleton()` |
| `widgets/manage` | `DashboardStatsSkeleton()` |

### Spinner 컴포넌트

#### Props

| Prop | 타입 | 설명 |
|---|---|---|
| `size` | `"sm"` \| `"md"` | 크기. 기본값 `"sm"` |

#### 스타일

- CSS 회전 애니메이션
- 현재 텍스트 색상 상속 (`currentColor`)

#### 사용

```tsx
// 기존
<button disabled={deleteBusy}>
  {deleteBusy ? "삭제 중..." : "삭제"}
</button>

// 변경
<button disabled={deleteBusy}>
  {deleteBusy ? <><Spinner size="sm" /> 삭제 중</> : "삭제"}
</button>
```

### Empty State 컴포넌트

데이터가 없는 상태를 표시하는 공통 컴포넌트. 아이콘과 메시지를 조합한다.

#### Props

| Prop | 타입 | 설명 |
|---|---|---|
| `icon` | `ReactNode` | 빈 상태 아이콘 |
| `message` | `string` | 빈 상태 메시지 |

#### 스타일

- `border-dashed border-border-3` 테두리 (기존 패턴 유지)
- `bg-background-1` 배경
- `text-text-3` 텍스트 색상
- 중앙 정렬, `py-12` 패딩

#### 적용 위치

| 위치 | 메시지 |
|---|---|
| 홈 - 글 목록 | 글이 없을 때 |
| 검색 결과 | 결과가 없을 때 |
| 태그 목록 | 태그가 없을 때 |
| Admin 글 관리 | 조건에 맞는 글이 없을 때 |
| Admin 방명록 관리 | 방명록이 없을 때 |
| Admin 댓글 관리 | 댓글이 없을 때 |
| 댓글 섹션 | 댓글이 없을 때 |

### 데이터 흐름

```
페이지 전환 로딩:
  Next.js 라우트 이동 → loading.tsx → Skeleton 표시

초기 데이터 로딩:
  useQuery isPending → Skeleton 표시

리페칭:
  useQuery isFetching (not isPending) → 인라인 텍스트 표시

액션 로딩:
  useMutation isPending → 버튼 Spinner + disabled

빈 상태:
  data.length === 0 → EmptyState 컴포넌트 표시
```

현재 패턴(`loading.tsx` + React Query)을 유지한다. 향후 Suspense 기반 스트리밍 SSR로 전환하여 컴포넌트 단위 로딩을 적용할 수 있다.

### 컴포넌트 구조 (FSD)

| 계층 | 컴포넌트 | 역할 |
|---|---|---|
| `shared` | `Skeleton` | Skeleton 로딩 primitive |
| `shared` | `Spinner` | 회전 로딩 인디케이터 |
| `shared` | `EmptyState` | 빈 상태 표시 (아이콘 + 메시지) |
| `app` | `loading.tsx` | 페이지 전환 Skeleton (Skeleton 컴포넌트 사용) |
| `app` | `dashboard/loading.tsx` | 대시보드 전환 Skeleton |

## API 연동

없음. 순수 클라이언트 UI 컴포넌트.

## 수용 기준

- [ ] `Skeleton` 공유 컴포넌트가 `@shared/ui`에 존재한다
- [ ] `Skeleton`이 `text`, `circle`, `rect` variant를 지원한다
- [ ] 기존 7개 로컬 Skeleton 정의가 공유 컴포넌트로 교체된다
- [ ] `Spinner` 공유 컴포넌트가 `@shared/ui`에 존재한다
- [ ] 버튼 액션 로딩 시 Spinner가 표시되고 버튼이 비활성화된다
- [ ] `EmptyState` 공유 컴포넌트가 `@shared/ui`에 존재한다
- [ ] `EmptyState`에 아이콘과 메시지가 표시된다
- [ ] 기존 빈 상태 코드가 `EmptyState` 컴포넌트로 교체된다
- [ ] `loading.tsx` 파일들이 `Skeleton` 컴포넌트를 사용한다
- [ ] 다크모드 자동 적용
- [ ] 접근성: Skeleton 영역에 `aria-busy="true"`, Spinner에 `role="status"` + 스크린리더 텍스트 (A-01 참조)
- [ ] Storybook story 작성 (F-38 참조)

## 에지 케이스

| 케이스 | 처리 |
|---|---|
| Skeleton 표시 후 에러 발생 | Skeleton → 에러 페이지 전환 (F-12) |
| 빈 상태에서 데이터 추가 후 복귀 | 빈 상태 → 데이터 목록으로 자연스럽게 전환 |
| 버튼 Spinner 중 네트워크 에러 | Spinner 해제 + Toast 에러 메시지 (F-14) |
| 리페칭 중 페이지 이동 | React Query가 자동 취소, 새 페이지 로딩 시작 |

## 의존성

- Blocked by: 없음
- Blocks: 없음
