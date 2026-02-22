# Client Progress - 2026-02-07

## ✅ 완료: ESLint 9 Flat Config 마이그레이션

### 1. eslint-config-pyosh 업데이트

- eslint-config-pyosh: 3.3.1 → 4.0.0 (MAJOR)
- eslint: 8.57.1 → 9.39.2 (MAJOR)
- @next/eslint-plugin-next: 13.5.11 → 15.5.12

### 2. 설정 파일 마이그레이션

- `.eslintrc` (Legacy) → `eslint.config.js` (Flat Config, ESM)
- lint 스크립트에서 `--ext` 플래그 제거

### 3. 코드 수정

- Prettier 포맷팅 auto-fix (17건)

### 검증 결과

- ✅ `pnpm lint` 통과 (에러 0, 경고 0)
- ✅ Peer dependency mismatch 완전 해소

## ✅ 완료: Phase A - App Router 마이그레이션 사전 준비

### A-1. TailwindCSS 설치 및 설정

- tailwindcss 4.1.18 + @tailwindcss/postcss + postcss 설치
- postcss.config.mjs 생성
- src/styles/globals.css 생성
  - 기존 28개 테마 토큰 → Tailwind @theme 매핑
  - CSS Reset, Font Scale, Theme Transition 통합

### A-2. Client 타입 오류 수정

- Button.tsx: `[string, string]` 명시적 타입 선언
- Text.tsx: `Omit<..., "onToggle">` 충돌 해결
- ✅ `pnpm compile:types` 통과

### A-3. Navigation Link 전환

- Navigation.tsx, Logo: `<a>` → `next/link` `<Link>`
- Footer.tsx: 외부 링크 `<a>` 유지

## ✅ 완료: Phase B - app/ 디렉토리 구조 생성

### B-1. 루트 레이아웃 (Server Component)

- `app/layout.tsx`: cookies() API로 테마 읽기
- `body[data-theme]` 설정
- Metadata API: title, icons, manifest, themeColor

### B-2. 클라이언트 Providers ("use client")

- `app/providers.tsx`: ToggleThemeProvider + Global + PageLayout
- `useToggleTheme.tsx`: `initialTheme` prop 추가

### 검증 결과

- ✅ `pnpm build` 성공 (pages/ + app/ 공존)
- ✅ `pnpm lint`, `pnpm compile:types` 통과

## ✅ 완료: Phase C - 페이지 마이그레이션

### C-1. 홈페이지 이관

- `app/page.tsx` 생성
- `pages/index.tsx` → `app/page.tsx` 이관
- `"use client"` 추가 (useCapture, Button onClick)

### C-2. 포트폴리오 페이지 이관

- `app/portfolio/page.tsx` 생성
- `pages/portfolio.tsx` → `app/portfolio/page.tsx` 이관

### 결과

- ✅ 두 페이지 모두 App Router로 이관 완료
- ⚠️ pages/ + app/ 공존 상태

## 다음 단계

- Phase D: Component 경계 설정
- Phase E: 테마 시스템 검증
