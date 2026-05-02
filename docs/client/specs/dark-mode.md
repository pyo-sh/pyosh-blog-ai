# F-17: 다크 모드

**상태:** DONE
**최종 수정:** 2026-05-02

---

## 1. 개요

CSS 변수 기반 다크/라이트 테마 시스템. 사용자 선택을 쿠키로 저장하고, 선택이 없으면 시스템 설정을 따른다.

## 2. 배경 및 동기

블로그 방문자에게 시각적 편의를 제공한다. 어두운 환경에서의 가독성, 눈의 피로 감소, 개인 선호 반영을 위해 다크 모드를 지원한다.

## 3. 목표

- 방문자가 다크/라이트 테마를 선택할 수 있다
- 선택하지 않은 경우 시스템 설정을 따른다
- 선택을 저장하여 재방문 시 유지한다
- 테마 전환 시 부드러운 트랜지션을 제공한다
- 첫 방문 시 FOUC(Flash of Unstyled Content) 없이 올바른 테마가 적용된다

## 4. 비목표

- 3번째 테마 (시스템 따르기 명시적 옵션)
- 커스텀 테마/색상 편집
- 페이지별 테마 설정

---

## 5. 상세 설계

### 5.1 사용자 흐름

1. 첫 방문 (쿠키 없음) → 시스템 `prefers-color-scheme`에 따라 테마 적용
2. 헤더의 테마 토글 버튼 클릭 → 테마 전환 + 쿠키 저장
3. 재방문 → 쿠키에서 저장된 테마 적용

### 5.2 UI 구성

#### 테마 토글 버튼

- 헤더에 배치
- 라이트 모드: Sun 아이콘 표시 (클릭 시 다크로 전환)
- 다크 모드: Night 아이콘 표시 (클릭 시 라이트로 전환)
- 2상태 토글 (dark ↔ light)

### 5.3 데이터 흐름

#### 테마 결정 우선순위

```
1. 쿠키에 명시적 선택이 있으면 → 해당 테마 적용
2. 쿠키가 없으면 → CSS @media (prefers-color-scheme: dark) 자동 적용
3. 시스템 설정도 없으면 → light 기본값
```

#### 서버-클라이언트 동기화

```
Server (layout.tsx)
  └─ cookies().get("theme") → data-theme 속성 설정
       └─ 쿠키 있음 → <body data-theme="dark|light">
       └─ 쿠키 없음 → <body> (data-theme 미설정, CSS 미디어 쿼리로 폴백)

Client (ThemeProvider)
  └─ initialTheme을 서버에서 전달받아 Context 초기화
  └─ toggleTheme() → data-theme 변경 + 쿠키 저장
```

#### FOUC 방지

쿠키가 없는 첫 방문 시에도 CSS `@media (prefers-color-scheme: dark)` 규칙이 브라우저 렌더링 전에 적용되므로 JS 실행 없이 올바른 테마가 표시된다. 별도의 인라인 스크립트가 필요 없다.

```css
/* CSS 우선순위 */
body { /* light 기본값 */ }
@media (prefers-color-scheme: dark) { body { /* dark 값 */ } }
body[data-theme="light"] { /* 명시적 light override */ }
body[data-theme="dark"]  { /* 명시적 dark override */ }
```

### 5.4 컴포넌트 구조 (FSD)

| 계층 | 컴포넌트 | 역할 |
|---|---|---|
| `app` | `layout.tsx` | 서버에서 쿠키 읽어 `data-theme` 설정 |
| `app-layer` | `ThemeProvider` | 테마 Context 제공, 토글/쿠키 관리 |
| `app-layer` | `theme.css` | 시맨틱 컬러 토큰 정의 (light/dark) |
| `app-layer` | `transition.css` | 테마 전환 트랜지션 유틸리티 |
| `widgets` | `ThemeButton` | 헤더 내 토글 버튼 (Sun/Night 아이콘) |
| `shared` | `useTheme` | 테마 상태 접근 훅 |

## 6. 테마 시스템

### 시맨틱 컬러 토큰

| 카테고리 | 토큰 | 설명 |
|---|---|---|
| Background | `background-1` ~ `background-4` | 배경색 4단계 (밝음 → 어두움) |
| Text | `text-1` ~ `text-4` | 텍스트색 4단계 (진함 → 연함) |
| Border | `border-1` ~ `border-2` | 테두리 |
| Primary | `primary-1` ~ `primary-2` | 주요 강조색 |
| Secondary | `secondary-1` | 보조 강조색 |
| Positive/Negative | `positive-1`, `negative-1` | 성공/에러 |
| Grey | `grey-1` ~ `grey-2` | 중립색 |

컬러 값은 디자인 작업 시 변경될 수 있다. 토큰 구조만 확정.

### 트랜지션

| 유틸리티 클래스 | 대상 속성 |
|---|---|
| `transition-theme` | color, background-color, border-color, box-shadow |
| `transition-color` | color |
| `transition-bg-color` | background-color |
| `transition-svg-color` | SVG fill, stroke |
| `transition-svg-bg-color` | SVG background |

- `transition-theme`에 `border-color`, `box-shadow` 추가 (현재 대비 변경사항)
- 전환 시간: color 0.25s, background-color 0.4s

### 컴포넌트별 세밀한 제어

시맨틱 토큰으로 커버되지 않는 예외적 스타일이 필요한 경우:

1. **컴포넌트 전용 토큰 추가** (반복 사용 시) - `theme.css`에 변수 추가
2. **`data-theme` 셀렉터 직접 사용** (일회성 예외) - 컴포넌트 CSS에서 직접 분기

두 방법 모두 `theme.css` 중앙 관리 원칙을 유지한다.

## 7. 수용 기준

- [ ] 헤더에 테마 토글 버튼이 표시된다
- [ ] 토글 클릭 시 dark ↔ light 전환된다
- [ ] 테마 선택이 쿠키에 저장되어 재방문 시 유지된다
- [ ] 쿠키 없는 첫 방문 시 시스템 `prefers-color-scheme`을 따른다
- [ ] 시스템 설정도 없으면 light가 기본값이다
- [ ] 테마 전환 시 color, background-color, border-color, box-shadow가 부드럽게 전환된다
- [ ] FOUC 없이 올바른 테마가 즉시 적용된다
- [ ] 모든 컴포넌트가 시맨틱 토큰을 사용하여 테마 일관성을 유지한다
- [ ] SSR 시 서버에서 쿠키 기반으로 올바른 `data-theme`이 설정된다
- [ ] 접근성: 토글 버튼에 적절한 aria-label (A-01 참조)

## 8. 에지 케이스

| 케이스 | 처리 |
|---|---|
| 쿠키 없음 + 시스템 dark | CSS `@media` 규칙으로 dark 적용 |
| 쿠키 없음 + 시스템 light | CSS 기본값 light 적용 |
| 쿠키 없음 + 시스템 설정 없음 | light 기본값 |
| 쿠키 값이 유효하지 않음 | 쿠키 무시, 시스템 설정 폴백 |
| JS 비활성화 | CSS `@media` 규칙으로 시스템 테마 적용, 토글 불가 |
| 하이드레이션 전 토글 클릭 | `isMounted` 체크로 마운트 전 버튼 미렌더링 |

## 9. 의존성

- 없음 (기반 기능)

## 10. 미해결 사항

없음. 모든 사항 확정됨.
