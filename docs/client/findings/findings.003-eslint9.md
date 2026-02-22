# ESLint 9 Flat Config 마이그레이션 (2026-02-07)

## 배경

ESLint 8.57.1이 deprecated 상태이고, peer dependency 불일치 경고가 발생하여 ESLint 9 + Flat Config로 마이그레이션 결정.

## 작업 내용

### 1. eslint-config-pyosh 업데이트

```
eslint-config-pyosh: 3.3.1 → 4.0.0 (MAJOR)
eslint: 8.57.1 → 9.39.2 (MAJOR)
@eslint/js: 신규 설치 9.39.2
globals: 신규 설치 15.15.0
eslint-import-resolver-typescript: 3.x → 4.4.4
@next/eslint-plugin-next: 13.5.11 → 15.5.12
eslint-config-next: 제거 (Flat Config에서 플러그인 직접 사용)
```

### 2. 설정 파일 마이그레이션

**`.eslintrc` (Legacy) → `eslint.config.js` (Flat Config)**

- `client/.eslintrc` 삭제
- `client/eslint.config.js` 생성 (ESM)

### 3. lint 스크립트 업데이트

```json
// Before
"lint": "eslint --ext .js,.jsx,.ts,.tsx src"

// After
"lint": "eslint src"
```

`--ext` 플래그는 ESLint 9에서 제거됨.

### 4. 코드 수정

**Client Prettier 포맷팅:**

- `Button.tsx`, `Modal.tsx`, `transition.ts` - `eslint --fix`로 자동 수정 (17건)

## 검증 결과

✅ `pnpm lint` 통과 (에러 0, 경고 0)

## 해결된 이슈

### Peer Dependency Mismatch 해소

```
Before:
  eslint-config-pyosh 3.3.1
    ├── ✕ @typescript-eslint/*@^6.8.0 (found 8.54.0)
    └── ✕ eslint-config-prettier@^9.0.0 (found 10.1.8)

After:
  eslint-config-pyosh 4.0.0
    ├── ✓ @typescript-eslint/*@^8.54.0 (found 8.54.0)
    ├── ✓ eslint-config-prettier@^10.1.8 (found 10.1.8)
    ├── ✓ eslint@^9.0.0 (found 9.39.2)
    └── ✓ 모든 peer dependency 충족
```

### Deprecated Warning 해소

```
Before: ❌ eslint@8.57.1 - "This version is no longer supported"
After:  ✅ eslint@9.39.2 - 최신 지원 버전
```

## 성과 측정

| 지표                     | Phase 0               | 현재                    | 개선 |
| ------------------------ | --------------------- | ----------------------- | ---- |
| ESLint                   | 8.57.1 (deprecated)   | 9.39.2                  | ✅   |
| eslint-config-pyosh      | 3.3.1 (peer mismatch) | 4.0.0                   | ✅   |
| ESLint 설정 형식         | .eslintrc (Legacy)    | eslint.config.js (Flat) | ✅   |
| Peer Dep 경고 (Client)   | 2개                   | 0개                     | ✅   |
| @next/eslint-plugin-next | 13.5.11               | 15.5.12                 | ✅   |

## 교훈

- ESLint 9 Flat Config는 설정 파일이 더 명시적이고 타입 안전함
- `--ext` 플래그 제거로 CLI 단순화
- eslint-config-pyosh 4.0.0이 ESLint 9를 완전 지원

## 관련 파일

- `client/eslint.config.js`
- `client/package.json`
