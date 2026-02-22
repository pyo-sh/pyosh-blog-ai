# Phase 0: Express 5.x 업그레이드 (2026-02-06)

## 작업 내용

### 1. 보안 패치

**업데이트된 패키지:**

```
express: 4.22.1 → 5.2.1 (MAJOR)
passport: 0.6.0 → 0.7.0
typeorm: 0.3.12 → 0.3.28
multer: 1.4.5 → 2.0.2 (MAJOR)
sinon: 15.2.0 → 21.0.1 (MAJOR)
supertest: 6.3.4 → 7.2.2 (MAJOR)
```

**보안 상태:**

- **11개 취약점 남음** (High: 6, Moderate: 1, Low: 4)
- 모든 취약점은 `swagger-express-ts`의 내부 의존성에서 발생
- 우리가 직접 사용하는 Express 5.2.1은 안전함

### 2. Express 4 → 5 Major Update

⚠️ **Breaking changes 존재**

- 테스트 필요 (특히 미들웨어, 에러 핸들링)
- [Express 5.x 마이그레이션 가이드](http://expressjs.com/en/guide/migrating-5.html) 참조

**주요 변경사항:**

- `app.del()` → `app.delete()`
- `req.param()` 제거 → `req.params`, `req.body`, `req.query` 사용
- `res.json()`, `res.jsonp()` 더 엄격한 타입 체크
- Promise rejection 자동 처리 (express-async-errors 일부 불필요)

### 3. swagger-express-ts 이슈

**문제:**

- 2019년 이후 업데이트 없음 (abandoned)
- 내부적으로 구버전 Express 의존
- 11개 보안 취약점의 원인

**권장 교체 옵션:**

- Option A: `@nestjs/swagger` (NestJS 스타일과 호환)
- Option B: `swagger-jsdoc` + `swagger-ui-express`
- Option C: Swagger 제거 후 다른 API 문서 도구

### 4. TypeScript & Linter 업데이트

```
typescript: 4.9.5 → 5.9.3
@typescript-eslint/eslint-plugin: 5.62.0 → 8.54.0
@typescript-eslint/parser: 5.62.0 → 8.54.0
prettier: 2.8.8 → 3.8.1
eslint-config-prettier: 8.10.2 → 10.1.8
eslint-plugin-prettier: 4.2.5 → 5.5.5
@types/chai-http 제거 (deprecated)
```

**TypeScript 5.x 컴파일 결과:**
✅ **컴파일 성공** (타입 오류 없음)

## Breaking Changes 요약

| 패키지     | 변경        | Breaking Changes  | 대응 필요도 |
| ---------- | ----------- | ----------------- | ----------- |
| Express    | 4.x → 5.x   | Yes (high)        | **높음**    |
| multer     | 1.x → 2.x   | Yes (minor)       | 낮음        |
| TypeScript | 4.9 → 5.9   | Yes (strictness)  | 중          |
| Prettier   | 2.x → 3.x   | Yes (formatting)  | 낮음        |
| Sinon      | 15.x → 21.x | Yes (API changes) | 중          |
| Supertest  | 6.x → 7.x   | Yes (minor)       | 낮음        |

## 다음 우선순위 액션

### 즉시 (Phase 0 후속)

1. ✅ Express 5.x 호환성 테스트
   - 서버 실행 테스트: `pnpm dev`
   - 기존 API 엔드포인트 동작 확인
   - 에러 핸들링 미들웨어 검증

2. ⏸️ swagger-express-ts 교체 (Phase S-5에서)

### 중기 (1-2주)

1. 전체 테스트 실행
2. 코드 포맷팅 (Prettier 3.x 적용)

## 발견된 추가 이슈

**Deprecated Warnings:**

```
❌ eslint@8.57.1 - "This version is no longer supported"
   → ESLint 9.x로 업그레이드 필요

❌ glob@9.3.5 - "Old versions not supported"
   → glob@11.x 업그레이드 필요
```

**Peer Dependency Mismatches:**

```
Server:
  swagger-express-ts 1.1.0
    ├── ✕ body-parser@^1.18.3 (found 2.2.2)
    ├── ✕ express@^4.16.4 (found 5.2.1)
    └── ✕ reflect-metadata@^0.1.10 (found 0.2.2)
```

## 성과 측정

| 지표            | Before | After  | 개선           |
| --------------- | ------ | ------ | -------------- |
| TypeScript 버전 | 4.9.5  | 5.9.3  | ✅             |
| Server 취약점   | 11개   | 11개   | (swagger 이슈) |
| Express         | 4.22.1 | 5.2.1  | ✅             |
| Prettier        | 2.8.8  | 3.8.1  | ✅             |
| TypeORM         | 0.3.12 | 0.3.28 | ✅             |

## 결론

Phase 0 목표 달성 (일부)

- TypeScript & 린터 현대화 완료
- Express 5.x 업그레이드 완료
- swagger-express-ts 이슈는 교체로 해결 필요

## 관련 파일

- `server/package.json`
- `server/tsconfig.json`
- `server/src/app.ts`
- `server/src/loaders/`
