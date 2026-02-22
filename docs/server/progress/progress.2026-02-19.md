## ✅ 완료: Task 03 - 테스트 인프라 설정

### 작업 내용
- `.env.test` 생성 (테스트 전용 DB: `pyosh_blog_test`, dummy OAuth 자격증명)
- `src/shared/env.ts` 수정 — `NODE_ENV=test` 시 `.env.test` 로드 지원
- `test/setup.ts` (Vitest globalSetup) — DB 생성 + drizzle migrate (멱등)
- `test/helpers/app.ts` — `createTestApp`, `injectAuth`, `cleanup`
- `test/helpers/seed.ts` — `seedAdmin`, `seedCategory`, `seedPost`, `seedTag`, `truncateAll`
- `vitest.config.ts` 업데이트 — `globalSetup`, `env.NODE_ENV=test`, `testTimeout:10000`, `include: test/**/*.test.ts`

### 의존성 추가/제거
- 없음 (기존 `dotenv`, `mysql2`, `drizzle-orm`, `vitest` 활용)

### 수정/생성/삭제된 파일
- `server/.env.test` (신규)
- `server/src/shared/env.ts` (수정 - test env 지원)
- `server/test/setup.ts` (신규)
- `server/test/helpers/app.ts` (신규)
- `server/test/helpers/seed.ts` (신규)
- `server/vitest.config.ts` (수정)
- `docs/server/tasks/task-03-test-infra.md` (체크박스 업데이트)

### 검증 결과
- ✅ `pnpm compile:types` 통과
- ✅ `pnpm test` 통과 (globalSetup: DB ready + migrations applied, smoke test 2개 통과)

### 이슈 & 해결
- **MySQL 권한 문제**: `pyosh` 유저가 `pyosh_blog_test` 생성 권한 없음 → setup.ts에서 `ER_DBACCESS_DENIED_ERROR` 잡아 graceful 처리 + 안내 메시지 출력
- **선행 조건**: 최초 1회 MySQL root로 DB 생성 + GRANT 필요 (task 문서에 기록)

### 성과
- 전체 테스트 인프라 구축 완료
- 향후 통합 테스트는 `createTestApp` + `seedXxx` + `truncateAll` 패턴으로 작성 가능

### 다음 단계
- Task 04 이후 실제 API 통합 테스트 작성

---

## ✅ 완료: Task 04 - Auth 모듈 Integration Test

### 작업 내용
- `test/routes/auth.test.ts` 생성 (8개 테스트 케이스)
- `setup` / `login` / `me` / `logout` 엔드포인트 전체 커버
- `.env.test`에 `BASE_URL=http://localhost:3000` 추가 (시스템 환경변수 충돌 해결)

### 의존성 추가/제거
- 없음

### 수정/생성/삭제된 파일
- `server/test/routes/auth.test.ts` (신규)
- `server/.env.test` (수정 - BASE_URL 추가)
- `docs/server/tasks/task-04-test-auth.md` (체크박스 업데이트)

### 검증 결과
- ✅ 10개 테스트 전체 통과 (smoke 2 + auth 8)
- ✅ POST /api/auth/admin/setup → 201 (성공), 409 (중복)
- ✅ POST /api/auth/admin/login → 200 + 세션 쿠키 (성공), 401 (잘못된 비밀번호), 401 (없는 이메일)
- ✅ GET /api/auth/me → 200 (로그인), 401 (비로그인)
- ✅ POST /api/auth/admin/logout → 204 + 이후 /me 401 확인

### 이슈 & 해결
- **BASE_URL 환경변수 충돌**: 시스템 환경에 `BASE_URL=""`(빈 문자열)이 설정되어 `z.string().url()` 검증 실패 → `.env.test`에 `BASE_URL=http://localhost:3000` 명시적 추가로 해결

### 성과
- Auth API 핵심 시나리오 전체 커버 완료
- `beforeEach: truncateAll()` 패턴으로 테스트 격리 확인

### 다음 단계
- Task 05 이후 Posts/Categories 등 나머지 API 통합 테스트 작성

---

## ✅ 완료: Task 05 - Categories & Tags Integration Test

### 작업 내용
- `test/routes/categories.test.ts` 생성 (7개 테스트 케이스)
- `test/routes/tags.test.ts` 생성 (3개 테스트 케이스)
- `src/routes/categories/category.route.ts` 버그 수정 — GET 응답에 Date → ISO 문자열 변환 누락
- `vitest.config.ts` 수정 — `fileParallelism: false` 추가 (DB 공유 race condition 해결)

### 의존성 추가/제거
- 없음

### 수정/생성/삭제된 파일
- `server/test/routes/categories.test.ts` (신규)
- `server/test/routes/tags.test.ts` (신규)
- `server/src/routes/categories/category.route.ts` (수정 - serializeCategoryTree 헬퍼 추가, GET 두 핸들러 적용)
- `server/vitest.config.ts` (수정 - fileParallelism: false)
- `docs/server/tasks/task-05-test-taxonomy.md` (체크박스 업데이트)

### 검증 결과
- ✅ 20개 테스트 전체 통과 (smoke 2 + auth 8 + categories 7 + tags 3)
- ✅ GET /api/categories → 200 + 빈 배열
- ✅ GET /api/categories → 트리 구조 (parent.children[0].name 확인)
- ✅ POST /api/categories → Admin 201, 비인증 403
- ✅ PATCH /api/categories/:id → 이름 변경 200
- ✅ DELETE /api/categories/:id → 하위 카테고리 있으면 409, 빈 카테고리 204
- ✅ GET /api/tags → 목록 조회 200
- ✅ GET /api/tags?keyword=react → 검색 결과 1건
- ✅ POST /api/admin/posts with tags → GET /api/tags에서 자동 생성 확인
- ✅ `pnpm lint` 통과 (기존 warning만, 에러 없음)

### 이슈 & 해결
- **ResponseSerializationError**: `GET /api/categories` 핸들러가 Date 객체를 그대로 반환 → Zod schema 불일치(500) → `serializeCategoryTree()` 헬퍼로 재귀 변환
- **테스트 파일 병렬 실행**: 여러 파일이 같은 DB를 공유하여 race condition 발생 (ER_DUP_ENTRY, 404) → `fileParallelism: false`로 파일 순차 실행

### 성과
- Taxonomy API(Categories, Tags) 핵심 시나리오 전체 커버
- 기존 루트 버그(Date 직렬화 누락) 발견 및 수정

### 다음 단계
- Task 06 이후 Posts API 통합 테스트 작성
