# FSD 마이그레이션 완료 및 TailwindCSS v4 완성 (2026-02-09)

## 배경

사용자가 직접 Client를 FSD (Feature-Sliced Design) 구조로 마이그레이션하고 모든 Emotion 코드를 제거함. 설정 파일/의존성 정리 및 CSS 구조 최적화 작업 수행.

## 발견된 이슈

### Critical (빌드 실패 가능)

1. **CSS import 파일명 불일치** - `index.css`가 `animations.css`/`transitions.css`(복수) 참조하지만 실제는 `animation.css`/`transition.css`(단수)
2. **@theme 토큰 vs 클래스명 불일치** - @theme: `--color-text1` → 클래스: `text-text1`, 하지만 소스코드는 `text-text-1`(하이픈) 사용

### High (설정 오염)

3. `next.config.js`: `compiler: { emotion: true }` 불필요
4. `tsconfig.json`: `jsxImportSource: "@emotion/react"` 불필요
5. `package.json`: @emotion/\* 3개 패키지 미사용
6. `tailwind.config.ts`: 경로 오류, v3 패턴으로 v4에서 불필요

### Medium (중복/정리)

7. `index.css`와 `theme.css` 모두 @theme 블록 중복
8. `transition.css` `:root` 변수 중복
9. `utility.css`: Tailwind v4 빌트인과 중복
10. `image-box.tsx`: 인라인 스타일 `var()` 수정 필요

## 해결 방법

### Phase C-1: Emotion 잔재 제거

- next.config.js `compiler.emotion` 블록 제거
- tsconfig.json `jsxImportSource` 제거
- @emotion/cache, @emotion/react, @emotion/styled 제거
- tailwind.config.ts 삭제
- tailwindcss 직접 의존성 추가 (pnpm hoisting 대응)

### Phase C-2: CSS 구조 정리

**전략**: theme.css의 `var()` 간접 참조 패턴 채택

**index.css 개편:**

- import 파일명 수정 (animations→animation, transitions→transition)
- theme.css import 추가
- @theme 블록, body 테마 정의 제거
- Google Fonts 최상단 이동

**theme.css @theme 토큰 리네임 (28개 색상 + 3개 타이밍):**

```css
/* Before */
--color-text1: var(--text1);
/* After  */
--color-text-1: var(--text1);
```

**기타:**

- `transition.css` `:root` 블록 제거
- `utility.css` 삭제
- `typography.css` `@apply` 제거 (v4 제약)
- `image-box.tsx` CSS 변수 하이픈 수정

### Phase C-3 + C-4: VS Code 설정

- `.vscode/settings.json`: Tailwind IntelliSense 설정 추가
- `.vscode/extensions.json`: Tailwind 추천 추가
- `.vscode/launch.json`: pnpm + 이름 수정

## Tailwind v4 특이사항

### CSS-First 설정

- `tailwind.config.ts` 불필요
- `@import "tailwindcss"` + `@theme` 블록으로 설정
- PostCSS 플러그인만 등록

### @apply 제약

- Tailwind v4에서 `@apply`는 빌트인 유틸리티만 참조 가능
- 커스텀 클래스는 `@apply` 불가
- 해결: `@layer base`에서 직접 CSS 속성 사용

### pnpm strict hoisting

- `tailwindcss`가 내부 의존성으로만 존재
- webpack이 `@import "tailwindcss"` 해석 실패
- 해결: `tailwindcss`를 직접 의존성으로 추가

### IntelliSense 제한

- `tailwindCSS.experimental.configFile` 설정 필요
- 커스텀 @theme 토큰 자동완성 제한적
- `text-h1` 등 커스텀 유틸리티는 자동완성 안 될 수 있음

## CSS 최종 구조

```
index.css          — @import 허브
├── Google Fonts   — url(...) 최상단
├── tailwindcss    — Tailwind v4 base
├── theme.css      — :root 팔레트 + @theme + body 테마
├── animation.css  — @keyframes
├── initialize.css — CSS reset
├── transition.css — transition 유틸리티
└── typography.css — 폰트 + heading + text 유틸리티
```

**theme.css 아키텍처:**

```css
:root {
  --light-background1: #f9f9fa;
  --dark-background1: #131415;
}

@theme {
  --color-background-1: var(--background1); /* 하이픈 필수 */
  --transition-timing-color: 0.25s;
}

body {
  --background1: var(--light-background1);
  color: var(--text1);
  background-color: var(--background1);
}

@media (prefers-color-scheme: dark) {
  body {
    --background1: var(--dark-background1);
  }
}

body[data-theme="light"] {
  --background1: var(--light-background1);
}
body[data-theme="dark"] {
  --background1: var(--dark-background1);
}
```

## FSD 구조 긍정적 피드백

- FSD 구조 깔끔하게 구성 (app-layer/shared/widgets/entities/features)
- `"use client"` 8개 파일에만 정확 배치 (이전 20+개에서 개선)
- `cn()` 유틸리티 (`clsx` + `twMerge`) 잘 활용
- ThemeProvider (React Context) 깔끔하게 구현
- Icon 컴포넌트 Server Component 유지
- 레거시 디렉토리 완전 제거 (pages/, styles/, hooks/, components/)

## 검증 결과

- ✅ `pnpm lint` - 통과 (에러 0)
- ✅ `pnpm build` - 통과 (경고 0, 에러 0)
- 🔲 `pnpm dev` - 스모크 테스트 필요 (수동)

## 수정 파일 요약

| 파일                 | 변경                       |
| -------------------- | -------------------------- |
| `next.config.js`     | compiler.emotion 제거      |
| `tsconfig.json`      | jsxImportSource 제거       |
| `package.json`       | 5개 제거, tailwindcss 추가 |
| `layout.tsx`         | Emotion 주석 제거          |
| `tailwind.config.ts` | 삭제                       |
| `index.css`          | import 허브 개편           |
| `theme.css`          | @theme 토큰 하이픈 리네임  |
| `transition.css`     | :root 제거                 |
| `utility.css`        | 삭제                       |
| `typography.css`     | @apply 제거                |
| `image-box.tsx`      | var() 하이픈 수정          |
| `.vscode/*`          | Tailwind 설정 추가         |

## 성과

- ✅ Emotion 완전 제거
- ✅ TailwindCSS v4 완전 작동
- ✅ FSD 구조 전환 완료
- ✅ CSS 구조 최적화
- ✅ `"use client"` 최소화 (8개)
- ✅ 빌드 성공 (에러 0)

## 교훈

- TailwindCSS v4는 CSS-first 접근이 직관적
- @theme 토큰 네이밍은 하이픈 필수 (kebab-case)
- Emotion 제거로 App Router 호환성 문제 완전 해결
- FSD 구조가 컴포넌트 역할 분리에 효과적

## 관련 파일

- `client/src/app-layer/` (FSD 구조)
- `client/src/shared/` (공통 UI)
- `client/src/styles/` (CSS 파일)
- `client/next.config.js`
- `client/tsconfig.json`
- `client/package.json`
