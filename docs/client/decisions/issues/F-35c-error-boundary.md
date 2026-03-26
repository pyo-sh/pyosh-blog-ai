# [F-35c] 클라이언트 에러 수집

> React Error Boundary와 API 에러 로깅을 통해 클라이언트 에러를 체계적으로 수집한다. v1에서는 콘솔 로깅으로 운영한다.

## SPEC 참조

- `docs/specs/deploy-monitoring.md` (섹션 5.4 클라이언트 에러 수집)

## 상세 설계

### React Error Boundary

```typescript
// shared/ui/error-boundary.tsx
class ErrorBoundary extends React.Component {
  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('[React Error]', {
      error: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      url: window.location.href,
      timestamp: new Date().toISOString(),
    });
  }

  render() {
    if (this.state.hasError) {
      return <ErrorFallback />;  // F-12 에러 페이지 재사용
    }
    return this.props.children;
  }
}
```

- `app/layout.tsx`에서 최상위 래핑
- 렌더링 에러 캐치 + 콘솔 로깅
- 사용자에게는 F-12 에러 페이지 표시

### API 에러 로깅

```typescript
// shared/api/client.ts
async function clientFetch(url: string, options?: RequestInit) {
  const response = await fetch(url, options);

  if (!response.ok) {
    const error = await response.json();
    console.error('[API Error]', {
      url,
      method: options?.method || 'GET',
      status: response.status,
      error: error.message,
      timestamp: new Date().toISOString(),
    });
    throw new ApiResponseError(response.status, error);
  }

  return response;
}
```

- 모든 API 에러를 콘솔에 구조화 로깅
- 사용자에게는 토스트 또는 인라인 에러 메시지

### 미처리 에러 캐치

```typescript
// app/layout.tsx 또는 별도 스크립트
if (typeof window !== 'undefined') {
  window.addEventListener('unhandledrejection', (event) => {
    console.error('[Unhandled Rejection]', {
      reason: event.reason,
      timestamp: new Date().toISOString(),
    });
  });
}
```

### 컴포넌트 구조

| 계층 | 파일 | 역할 |
|---|---|---|
| 클라이언트 | `shared/ui/error-boundary.tsx` | React Error Boundary (신규) |
| 클라이언트 | `shared/api/client.ts` | API 에러 로깅 (기존 확장) |

### 클라이언트 변경 필요사항

| 항목 | 설명 |
|---|---|
| `error-boundary.tsx` | React Error Boundary 신규 |
| `client.ts` | API 에러 콘솔 로깅 추가 |
| `layout.tsx` | Error Boundary 래핑 + unhandledrejection 리스너 |

## API 연동

없음. 클라이언트 전용 에러 수집.

## 수용 기준

- [ ] React Error Boundary가 렌더링 에러를 캐치하여 에러 페이지를 표시한다
- [ ] API 에러가 구조화된 형태로 콘솔에 로깅된다
- [ ] 미처리 Promise rejection이 콘솔에 로깅된다
- [ ] Error Boundary 폴백 UI가 F-12 에러 페이지를 재사용한다

## 에지 케이스

| 케이스 | 처리 |
|---|---|
| Error Boundary 내부에서 에러 | React 기본 에러 처리로 폴백 |
| API 에러 응답이 JSON이 아님 | catch에서 raw text 로깅 |

## 의존성

- Blocked by: F-12
- Blocks: 없음
