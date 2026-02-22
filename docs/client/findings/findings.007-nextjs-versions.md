# Next.js 최신 버전 분석 (14→15→16) (2026-02-08)

## 배경

프로젝트의 Next.js 14.2.35를 최신 버전으로 업그레이드하기 위한 사전 조사. 2026년 2월 기준 최신 버전 분석 및 마이그레이션 경로 수립.

## 현재 최신 안정 버전 (2026년 2월 기준)

| 항목            | 현재 프로젝트 | 최신 안정 버전          | 비고                                    |
| --------------- | ------------- | ----------------------- | --------------------------------------- |
| **Next.js**     | 14.2.35       | **16.1.0** (2025-12-18) | 2 Major 버전 차이                       |
| **React**       | 18.2.0        | **19.2.1** (2025-12)    | 1 Major 버전 차이                       |
| **Node.js**     | 25.2.1        | 25.2.1 (Current)        | 충족 (최소 20.9+)                       |
| **TypeScript**  | 5.9.3         | 5.9.3                   | 충족 (최소 5.1+)                        |
| **TailwindCSS** | 4.1.18        | 4.1.18                  | **Next.js 16 Turbopack 빌드 오류 있음** |

## Next.js 14 → 15 Breaking Changes

Next.js 15는 2024년 10월 출시.

### (1) React 19 필수

- Next.js 15부터 React 19가 **최소 요구 버전**
- `react@19`, `react-dom@19` 설치 필수

### (2) Async Request APIs (핵심)

동기 방식이었던 API들이 **모두 비동기**로 변경:

```typescript
// Next.js 14 (동기)
const cookieStore = cookies();
const headersList = headers();
const { isEnabled } = draftMode();
const { slug } = params;

// Next.js 15+ (비동기)
const cookieStore = await cookies();
const headersList = await headers();
const { isEnabled } = await draftMode();
const { slug } = await params;
```

**프로젝트 영향:**

- `app/layout.tsx`에서 이미 `await cookies()` 사용 중 (호환됨)
- `params`, `searchParams` 사용하는 페이지에서 `await` 추가 필요

### (3) fetch() 캐싱 기본값 변경

- fetch 요청이 **더 이상 기본 캐시되지 않음**
- 캐시 필요 시 명시적으로 `cache: 'force-cache'` 지정

### (4) 설정 이름 변경

```javascript
// 14.x
experimental: {
  bundlePagesExternals: true,
  serverComponentsExternalPackages: ['package-name'],
}

// 15.x
bundlePagesRouterDependencies: true,
serverExternalPackages: ['package-name'],
```

## Next.js 15 → 16 Breaking Changes

Next.js 16은 2025년 10월 21일 출시.

### (1) Async Request APIs 동기 접근 완전 제거

- Next.js 15에서는 임시로 동기 접근 허용했으나, 16에서 **완전 제거**
- 모든 API에 `await` 필수

### (2) middleware.ts → proxy.ts 리네임

```typescript
// Next.js 15: middleware.ts
export function middleware(request: Request) {}

// Next.js 16: proxy.ts
export function proxy(request: Request) {}
```

- `edge` 런타임 미지원, `nodejs` 런타임 사용

### (3) Turbopack 기본 활성화

- Turbopack이 기본 빌드 도구로 전환 (webpack 대체)
- webpack 사용 시 `next build --webpack` 플래그 필요

### (4) next/image 변경사항

| 설정               | 이전 기본값 | 새 기본값       |
| ------------------ | ----------- | --------------- |
| `minimumCacheTTL`  | 60초        | 14400초 (4시간) |
| `imageSizes`       | 16 포함     | 16 제거됨       |
| `qualities`        | 1~100 전부  | [75]만          |
| `maximumRedirects` | 무제한      | 3회             |
| 로컬 IP            | 허용        | 차단            |

- `next/legacy/image` 제거 → `next/image` 사용
- `images.domains` 제거 → `images.remotePatterns` 사용

### (5) 제거된 기능

| 제거된 기능                                   | 대체 방안        |
| --------------------------------------------- | ---------------- |
| AMP 지원                                      | 완전 제거        |
| `next lint` 명령어                            | ESLint 직접 사용 |
| `serverRuntimeConfig` / `publicRuntimeConfig` | 환경 변수 사용   |
| `devIndicators` 옵션                          | 제거됨           |

## React 18 → 19 주요 변경사항

### (1) 핵심 API 변경

```typescript
// React 18
useFormState(action, initialState)

// React 19
useActionState(action, initialState, permalink?)
```

### (2) ref 처리 방식 변경

- React 19에서 ref가 일반 prop으로 전달됨
- `forwardRef` 더 이상 필요 없음 (deprecated 예정)

### (3) Context 사용 변경

```typescript
// React 18
<ThemeContext.Provider value={theme}>

// React 19
<ThemeContext value={theme}>  // .Provider 생략 가능
```

## Emotion 호환성 분석

### 현재 상태

| 항목            | 버전    | 상태                     |
| --------------- | ------- | ------------------------ |
| @emotion/react  | 11.14.0 | 최신 (1년+ 미업데이트)   |
| @emotion/styled | 11.14.1 | 최신 (7개월+ 미업데이트) |

### React 19 호환성: 해결됨

- @emotion/react 11.12.0에서 React 19 타입 호환성 수정
- @emotion/react 11.14.0에서 추가 안정화
- GitHub Issue #3186: **RESOLVED** (2024-12-11 종료)

### Next.js App Router 호환성: 비공식 지원

**중요 발견:**

- Next.js 공식 CSS-in-JS 가이드에서 Emotion은 **"currently working on support"** 상태
- 공식 지원 라이브러리 목록에 **Emotion 미포함**

**사용 가능하지만 추가 설정 필요:**

1. `"use client"` 지시문 필수
2. Style Registry 컴포넌트 권장 (SSR 스트리밍 지원)
3. Server Component에서는 Emotion API 사용 불가
4. Turbopack과의 호환성 이슈 보고됨

## TailwindCSS v4 호환성 분석

### Next.js 16 Turbopack 빌드 오류

- **문제**: TailwindCSS v4.1.18 + Next.js 16 Turbopack 조합에서 빌드 실패
- **에러**: `RangeError: Invalid code point 11025747`
- **원인**: Turbopack의 PostCSS 변환 단계 이슈

### 해결 방안

| 방안                             | 설명                                 | 권장도          |
| -------------------------------- | ------------------------------------ | --------------- |
| TailwindCSS 4.0.7로 다운그레이드 | 빌드 성공 확인됨                     | **높음** (임시) |
| TailwindCSS 패치 버전 대기       | 4.1.x 또는 4.2.x에서 수정 예상       | 중              |
| Next.js 15 유지                  | Turbopack 선택적 → webpack 사용 가능 | 상황에 따라     |

## 마이그레이션 전략 권장사항

### 단계별 업그레이드 경로

**Phase 1: Next.js 14.2.35 → 15.x (권장: 15.5.x)**

```
필수 작업:
1. React 18 → React 19 업그레이드
2. cookies(), headers() 등 async API 적용
3. fetch 캐싱 기본값 확인
4. @types/react, @types/react-dom 업데이트
5. 설정 이름 변경
```

**Phase 2: Next.js 15.x → 16.x**

```
필수 작업:
1. middleware.ts → proxy.ts 리네임 (해당 시)
2. Turbopack 호환성 확인
3. TailwindCSS 버전 조정 (4.0.7 또는 패치 대기)
4. next/image 설정 검토
5. AMP 코드 제거 (해당 시)
```

### 리스크 매트릭스

| 리스크                  | 심각도   | 대응 난이도 | 설명                      |
| ----------------------- | -------- | ----------- | ------------------------- |
| React 19 업그레이드     | **높음** | 중          | Emotion 호환성 확인 필요  |
| Async Request APIs      | 중       | 낮음        | 코드모드로 자동화 가능    |
| TailwindCSS + Turbopack | **높음** | 중          | 빌드 실패, 버전 조정 필요 |
| Emotion 비공식 지원     | 중       | 높음        | Style Registry 추가 설정  |

## 결론 및 권장사항

1. **즉시 업그레이드 비권장**: Next.js 16은 TailwindCSS v4.1.18과 호환 이슈
2. **Next.js 15.5.x를 중간 목표로 설정**: Turbopack 선택적이므로 안정적
3. **React 19 업그레이드 선행**: Emotion 11.14.x가 호환되므로 먼저 검증
4. **TailwindCSS 버전 모니터링**: 패치 후 Next.js 16 업그레이드
5. **장기적으로 Emotion → TailwindCSS 전환 가속**: 비공식 지원 감안

**핵심 판단:**

- 현재 시점에서 **Next.js 15.5.x + React 19.2 + TailwindCSS 4.1.18**이 가장 안정적
- Next.js 16은 TailwindCSS 호환 이슈 해결 후 업그레이드 권장

## 관련 파일

- `client/package.json`
- `client/next.config.js`
- `client/app/layout.tsx`
