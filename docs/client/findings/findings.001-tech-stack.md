# Client 기술 스택 분석 (2026-02-06)

## 배경

3년간 방치된 블로그 프로젝트의 현재 상태를 파악하고 현대화 전략 수립을 위한 초기 분석.

## 핵심 기술 스택

### 프레임워크

- **Next.js 13.1.6** (Pages Router, App Router 미사용)
- **React 18.2.0**
- **TypeScript 4.9.5** (strict mode)

### 스타일링

- **Emotion** (@emotion/react, @emotion/styled)
  - CSS-in-JS with styled components
  - Theme system (dark/light mode)
  - jsxImportSource: @emotion/react

### 프로젝트 구조

```
client/src/
├── components/     # React 컴포넌트
│   ├── libs/      # 재사용 가능한 기본 컴포넌트
│   ├── PageLayout.tsx
│   └── Header.tsx, Footer.tsx
├── pages/         # Next.js Pages Router
│   ├── _app.tsx
│   ├── _document.tsx
│   └── index.tsx
├── styles/        # Emotion 테마 & 글로벌 스타일
├── hooks/         # 커스텀 훅 (useToggleTheme)
└── utils/
```

## 코드 스타일

### 컴포넌트 패턴

```tsx
const PageLayout: React.FC<PropsWithChildren> = ({ children }) => {
  return <Wrapper>...</Wrapper>;
};
export default PageLayout;
```

### 스타일링 패턴

```tsx
const Wrapper = styled.div`
  color: ${({ theme }) => theme.text1};
  background-color: ${({ theme }) => theme.background1};
  ${TRANSITION_THEME}
`;
```

### 테마 시스템

- Dark/Light 테마 객체
- Cookie 기반 SSR 테마 동기화
- getInitialProps로 서버사이드 쿠키 읽기

## 발견된 이슈

### 버전 이슈

- Next.js 13.1.6 → 최신 15.x 업데이트 필요
- React 18.2.0 → 18.3.x
- TypeScript 4.9.5 → 5.x

### 보안 이슈

- .env 파일들이 git에 포함됨
- 20개 취약점 (Critical: 1, High: 9)

### 코드 품질

- TODO 주석 다수 (image 처리 미완성)
- Pages Router 사용 (App Router 검토 필요)

## 현대화 검토 항목

1. Next.js App Router 마이그레이션
2. Emotion vs Tailwind CSS 검토
3. 의존성 업데이트 전략
4. 테스트 커버리지 확인

## 관련 파일

- `client/package.json`
- `client/tsconfig.json`
- `client/src/styles/`
