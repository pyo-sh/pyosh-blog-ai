# Phase D: Client/Server Component 경계 설정 (2026-02-08)

## 배경

App Router 환경에서 모든 Emotion 사용 컴포넌트에 `"use client"` 지시문을 추가하여 Client/Server 경계를 명확히 설정.

## 작업 범위

총 20개 컴포넌트 처리.

## 처리된 컴포넌트

### Client Component 필수 (상호작용 있음)

1. `Header.tsx` - scroll 이벤트, useState
2. `ThemeChanger.tsx` - useToggleTheme 훅
3. `Button.tsx` - onClick 핸들러
4. `Modal.tsx` - createPortal, useState
5. `ImageBox.tsx` - onLoadingComplete, useState
6. `Text.tsx` - onClick, draggable 이벤트

### Emotion styled 컴포넌트

7. `PageLayout.tsx` - styled 사용
8. `Footer.tsx` - styled, useTheme 사용
9. `Navigation.tsx` - useTheme, css 사용
10. `Logo/index.tsx` - styled, useTheme 사용
11. `ProfileName.tsx` - styled, useTheme 사용
12. `SectionLayout.tsx` - styled 사용
13. `Contacts.tsx` - css, useTheme, useToggleTheme 사용
14. `Profile/index.tsx` - css, useTheme 사용
15. `Introduce.tsx` - css 사용
16. `Experience.tsx` - Client Component 사용
17. `Project.tsx` - css 사용
18. `List.tsx` - css 사용
19. `ListRow.tsx` - css 사용
20. `Spacing.tsx` - css 사용
21. `RowSpacing.tsx` - css 사용

### Server Component 유지

- Icon 컴포넌트 전체 (BrushIcon, GithubIcon, MailIcon 등) - 순수 SVG, Emotion 미사용

## 검증 결과

```bash
✅ pnpm lint - 에러 0, 경고 0
✅ pnpm compile:types - 타입 오류 0
```

## 핵심 인사이트

### Emotion + App Router 제약

- `styled.*`, `css()`, `useTheme()` 사용 시 무조건 `"use client"` 필요
- Server Component에서는 Emotion API 사용 불가
- CSS Variables (`body[data-theme]`)는 Server Component에서도 사용 가능

### Client/Server 경계 원칙

1. Emotion 사용 → Client Component
2. 상호작용 (useState, useEffect, onClick 등) → Client Component
3. 순수 렌더링 + Emotion 없음 → Server Component 가능

## 성과

- App Router 환경에서 명확한 Client/Server 경계 설정 완료
- Emotion 의존성이 있는 모든 컴포넌트 처리 완료
- 타입 안정성 및 린트 규칙 준수 확인

## 교훈

- Emotion은 App Router에서 비공식 지원 → 모든 사용처에 `"use client"` 필수
- Icon처럼 순수 JSX만 사용하는 컴포넌트는 Server Component로 유지 가능
- `"use client"` 경계를 최소화하는 것이 SSR 성능에 유리

## 다음 단계

- Phase E: 테마 시스템 App Router 호환 검증
- Phase C: Emotion 완전 제거 및 Tailwind 전환

## 관련 파일

- `client/src/components/**/*.tsx` (20개 파일)
