# Phase 0: 패키지 관리자 통일 및 보안 패치 (2026-02-06)

## 작업 내용

### 1. Package Manager 통일

- pnpm으로 완전 통일
- `@yarnpkg/pnpify` 제거
- yarn.lock, .yarnrc 삭제

### 2. 보안 패치

**업데이트된 패키지:**

```
jspdf: 2.5.2 → 4.1.0 (Critical 취약점 해결)
next: 13.5.11 → 14.2.35 (12개 취약점 해결)
```

**보안 개선:**

- Before: 20개 취약점 (Critical: 1, High: 9, Moderate: 8, Low: 2)
- After: 2개 취약점 (High: 1, Moderate: 1)
- **개선율: 90% 취약점 제거**

**남은 취약점:**

1. Next.js DoS (React Server Components) - 15.0.8 필요
2. Image Optimizer DoS - 15.5.10 필요

### 3. TypeScript & Linter 업데이트

```
typescript: 4.9.5 → 5.9.3
@typescript-eslint/eslint-plugin: 5.62.0 → 8.54.0
@typescript-eslint/parser: 5.62.0 → 8.54.0
prettier: 2.8.8 → 3.8.1
eslint-config-prettier: 8.10.2 → 10.1.8
eslint-plugin-prettier: 4.2.5 → 5.5.5
```

### 4. TypeScript 5.x 컴파일 결과

**타입 오류 4개 발견:**

1. `Button.tsx:56,61,64` - Color type 불일치
2. `Text.tsx:73` - onToggle event handler type 불일치

**분석:**

- TypeScript 5.x의 엄격한 타입 검사로 기존 숨어있던 타입 불안전성 발견
- 실제 런타임 오류는 아니지만, 타입 안정성 개선 필요

## Breaking Changes

| 패키지     | 변경        | Breaking Changes  | 대응 필요도 |
| ---------- | ----------- | ----------------- | ----------- |
| Next.js    | 13.1 → 14.2 | Yes (moderate)    | 중          |
| jspdf      | 2.x → 4.x   | Yes (API changes) | 중          |
| TypeScript | 4.9 → 5.9   | Yes (strictness)  | 중          |
| Prettier   | 2.x → 3.x   | Yes (formatting)  | 낮음        |

## 다음 우선순위 액션

1. ✅ Next.js 14.x 호환성 테스트
2. ✅ Client 타입 오류 수정
3. ⏸️ Next.js 15.x 업그레이드 (Phase A에서)

## 성과 측정

| 지표            | Before           | After     | 개선     |
| --------------- | ---------------- | --------- | -------- |
| TypeScript 버전 | 4.9.5            | 5.9.3     | ✅       |
| Client 취약점   | 20개             | 2개       | **90%↓** |
| Package Manager | pnpm + yarn 혼재 | pnpm 통일 | ✅       |
| Next.js         | 13.1.6           | 14.2.35   | ✅       |
| Prettier        | 2.8.8            | 3.8.1     | ✅       |

## 관련 파일

- `client/package.json`
- `client/tsconfig.json`
- `client/src/components/libs/Button.tsx`
- `client/src/components/libs/Text.tsx`
