# Phase A: App Router 사전 준비 - TailwindCSS v4 (2026-02-07)

## 배경

App Router 마이그레이션 전에 Emotion 의존성을 줄이고 Tailwind CSS v4를 도입하여 점진적 전환 준비.

## 작업 내용

### 1. TailwindCSS v4 설치 및 설정

**설치된 패키지:**

```
tailwindcss: 4.1.18
@tailwindcss/postcss: 4.1.18
postcss: 8.5.6
postcss-cli: 11.0.1
```

**생성된 파일:**

- `postcss.config.mjs` - @tailwindcss/postcss 플러그인 설정
- `src/styles/globals.css` - 통합 글로벌 스타일시트

### 2. globals.css 구성

```css
@import "tailwindcss" → Tailwind 기본 유틸리티
@theme { } → 기존 28개 CSS 변수를 Tailwind 색상 토큰으로 매핑
CSS Reset → initialize.css 통합
Font Scale → font.css 통합 (클래스명 text-h1~h6, text-r1~r6, text-e1~e6)
Theme Variables → light/dark 테마 CSS 변수 직접 선언
Transition Utilities → transition.ts의 7개 유틸리티를 CSS 클래스로 전환
```

### 3. Tailwind v4 접근 방식

- `tailwind.config.ts` 없음 (v4는 CSS-first 설정)
- `@theme` 블록으로 디자인 토큰 정의
- 기존 CSS 변수(`--background1` 등)를 Tailwind 색상으로 매핑
  → `bg-background1`, `text-text1`, `border-border3` 등으로 사용 가능

### 4. Emotion → TailwindCSS 전환 전략

1. 기존 Emotion과 Tailwind 병행 가능 (Phase A 단계)
2. 컴포넌트별 점진적 전환 (Phase D에서 실행)
3. 최종적으로 Emotion 의존성 완전 제거

### 5. Client 타입 오류 수정

**Button.tsx (3개 오류 → 0개):**

- 원인: `eTheme.text1`은 `Color` 타입인데 `"transparent"` (string) 할당 불가
- 수정: `let [color, backgroundColor]: [string, string]` 명시적 타입 선언

**Text.tsx (1개 오류 → 0개):**

- 원인: `as?: keyof JSX.IntrinsicElements`가 `details` 포함 → `onToggle` 이벤트 타입 충돌
- 수정: `Omit<React.HTMLAttributes<HTMLOrSVGElement>, "onToggle">` 적용
- React 18.3+에서 `ToggleEvent` 타입이 변경되어 발생한 호환성 문제

### 6. Navigation Link 전환

| 파일           | 변경                        | 이유                        |
| -------------- | --------------------------- | --------------------------- |
| Navigation.tsx | `<a href>` → `<Link href>`  | 내부 라우팅 (/, /portfolio) |
| Logo/index.tsx | `styled.a` → `styled(Link)` | 홈 링크 (/)                 |
| Footer.tsx     | 변경 없음                   | 외부 링크 (GitHub, mailto)  |

## 검증 결과

- ✅ `pnpm lint` 통과
- ✅ `pnpm compile:types` 통과

## 교훈

### Tailwind v4 특징

- CSS-first 설정 방식이 더 직관적
- `@theme` 블록으로 디자인 시스템 중앙화
- PostCSS 플러그인 하나로 완전 작동

### TypeScript 5.x 엄격함

- 숨어있던 타입 불안전성을 찾아냄
- React 18.3+ 타입 변경사항 주의 필요

## 다음 단계

- Phase B: App Router로 전환 (`pages/` → `app/`)
- Phase C: Emotion 제거 준비
- Phase D: 컴포넌트별 Tailwind 전환

## 관련 파일

- `client/postcss.config.mjs`
- `client/src/styles/globals.css`
- `client/src/components/libs/Button.tsx`
- `client/src/components/libs/Text.tsx`
- `client/src/components/Navigation.tsx`
