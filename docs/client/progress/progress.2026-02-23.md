# Progress — 2026-02-23

## #4 API 클라이언트 설정 (fetch wrapper + TanStack Query)

**PR**: [#19](https://github.com/pyo-sh/pyosh-blog-fe/pull/19) ✅ Merged

### 작업 내용

- `shared/api/types.ts` — 공통 타입 정의 (`PaginatedResponse<T>`, `ApiError`, `ApiResponseError`)
- `shared/api/client.ts` — fetch wrapper 구현
  - `serverFetch`: RSC 전용, 쿠키 헤더 직접 전달, `cache: no-store` 기본값
  - `clientFetch`: Client Component 전용, `credentials: include`로 브라우저 쿠키 자동 포함
- `shared/api/index.ts` — barrel export
- `app-layer/provider/query-provider.tsx` — TanStack Query Provider (SSR/CSR 분리 패턴)
- `app-layer/provider/index.tsx` — QueryProvider 통합
- `.env.local.example` — `NEXT_PUBLIC_API_URL=http://localhost:5500`
- `@tanstack/react-query 5.90.21` 설치

### 설계 노트

- QueryClient `staleTime` 60s (공개 데이터 기본값), `refetchOnWindowFocus: false`
- Admin 페이지에서는 개별 Query에서 `staleTime: 0` 오버라이드 예정
- SSR: 매 요청마다 새 QueryClient 생성, 브라우저: 싱글턴 유지 (hydration 안전)
