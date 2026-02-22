# Phase E: 테마 시스템 검증 (2026-02-08)

## 배경

App Router 환경에서 테마 시스템이 완전히 작동하는지 확인. Pages Router의 getInitialProps 방식에서 App Router의 cookies() API로 전환.

## 현재 구현 상태 (Phase B에서 완료)

### App Router 테마 흐름

**1. app/layout.tsx (Server Component)**

```typescript
const cookieStore = await cookies();
const themeType = cookieStore.get("theme")?.value ?? "";

return (
  <body data-theme={themeType}>
    <Providers initialTheme={themeType}>{children}</Providers>
  </body>
);
```

**2. app/providers.tsx (Client Component)**

```typescript
export default function Providers({ children, initialTheme }: Props) {
  return (
    <ToggleThemeProvider initialTheme={initialTheme}>
      <Global styles={globalTheme} />
      <PageLayout>{children}</PageLayout>
    </ToggleThemeProvider>
  );
}
```

**3. hooks/useToggleTheme.tsx**

```typescript
export function ToggleThemeProvider({
  children,
  initialTheme,
}: TProviderProps) {
  const [themeType, setThemeType] = useState<TThemeType>(
    initialTheme === "dark" || initialTheme === "light"
      ? initialTheme
      : "default",
  );
  const [isMounted, setIsMounted] = useState<boolean>(false);

  // hydration mismatch 방지
  useEffect(() => {
    setIsMounted(true);
    // fallback 로직...
  }, []);
}
```

## 검증 결과

### SSR 테마 동기화

- ✅ App Router: `cookies()` API 사용 (layout.tsx)
- ✅ Server-side에서 `body[data-theme]` 설정
- ✅ Client에게 `initialTheme` 전달

### useToggleTheme 독립성

- ✅ `initialTheme` prop 지원 (optional)
- ✅ getInitialProps 의존성 없음
- ✅ hydration mismatch 방지 (`isMounted` 플래그 사용)

### 호환성

- App Router: initialTheme prop 전달됨
- Pages Router: initialTheme 없이도 작동 (fallback 로직)
- 두 방식 모두 정상 작동

## 핵심 인사이트

### getInitialProps 의존성 제거

- useToggleTheme 자체는 getInitialProps에 의존하지 않음
- getInitialProps는 Pages Router의 \_app.tsx에만 존재
- App Router에서는 cookies() API 사용으로 완전 대체

### hydration mismatch 방지 전략

1. Server: `body[data-theme]` 설정
2. Client: `initialTheme` prop으로 초기값 동기화
3. Fallback: `isMounted` 후 `body.dataset.theme` 또는 `matchMedia` 확인

## Phase E 상태

- **이미 Phase B에서 구현 완료**
- 추가 작업 불필요
- App Router 테마 시스템 완전 작동

## 관련 파일

- `client/app/layout.tsx`
- `client/app/providers.tsx`
- `client/src/hooks/useToggleTheme.tsx`
