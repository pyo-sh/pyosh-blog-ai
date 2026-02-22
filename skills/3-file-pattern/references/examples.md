# 작업 예시

## 시나리오 1: Client 컴포넌트 개발

**사용자 요청**: "블로그 포스트 카드 컴포넌트를 만들어줘"

### 워크플로
1. `@docs/client/tasks/` 폴더 목록 확인 (관련 task 파일 찾기)
2. `tasks/task-02-page-routing.md` 읽기 (해당 작업)
3. `@docs/client/progress.index.md` 읽기 (최근 3개 항목)
4. `@docs/client/findings.index.md` 읽기 (TailwindCSS 관련 검색)
5. `findings/findings.002-tailwind-v4-tokens.md` 선택적 읽기
6. `@client/CLAUDE.md`에서 Next.js/TailwindCSS 규칙 확인
7. `src/shared/ui/post-card.tsx` 생성
8. `tasks/task-02-page-routing.md` 체크박스 업데이트
9. `progress/progress.2026-02-15.md` 생성 (상세 로그)
10. `progress.index.md`에 한줄 요약 추가

### 헬스체크
```text
--- healthcheck ---
area: client
mode: balanced
read: [tasks/task-02-page-routing.md, findings.index.md, findings.002, client/CLAUDE.md]
updated: [src/shared/ui/post-card.tsx, tasks/task-02-page-routing.md, progress.2026-02-15.md, progress.index.md]
--- end ---
```

---

## 시나리오 2: Server API 개발 + 새 기술 조사

**사용자 요청**: "포스트 목록 조회 API를 만들어줘. 페이지네이션 전략도 고민해야 해"

### 워크플로
1. `@docs/server/tasks/` 폴더 목록 확인
2. `tasks/task-06-test-posts.md` 읽기 (해당 작업)
3. `@docs/server/findings.index.md` 읽기 (페이지네이션 관련 없음 확인)
4. `@server/CLAUDE.md`에서 Fastify/Drizzle 규칙 확인
5. 페이지네이션 전략 조사 (cursor-based vs offset-based)
6. `findings/findings.004-pagination-strategy.md` 생성
7. `findings.index.md`에 항목 추가
8. `src/routes/posts.ts`에 GET /posts 라우트 추가
9. `tasks/task-06-test-posts.md` 체크박스 업데이트
10. `progress/progress.2026-02-15.md` 생성
11. `progress.index.md`에 한줄 요약 추가

### 헬스체크
```text
--- healthcheck ---
area: server
mode: balanced
read: [tasks/task-06-test-posts.md, findings.index.md, server/CLAUDE.md]
updated: [findings.004, findings.index.md, src/routes/posts.ts, tasks/task-06-test-posts.md, progress.2026-02-15.md, progress.index.md]
notes: 새 findings 생성 (pagination 전략)
--- end ---
```

---

## 시나리오 3: 영역 간 작업 전환

**사용자 요청**: "포스트 목록 API를 만들고, 그걸 사용하는 페이지도 만들어줘"

### 워크플로

#### Part 1: Server 작업
1. `@docs/server/tasks/` 목록 확인 → 해당 task 파일 읽기
2. `progress.index.md`, `findings.index.md` 읽기
3. API 구현
4. 해당 task 파일 체크박스 업데이트
5. `progress/progress.2026-02-15.md` 생성 (server)
6. `progress.index.md` 갱신 (server)

#### Part 2: Client 작업
7. `@docs/client/tasks/` 목록 확인 → 해당 task 파일 읽기
8. `progress.index.md`, `findings.index.md` 읽기
9. 페이지 구현
10. 해당 task 파일 체크박스 업데이트
11. `progress/progress.2026-02-15.md` 생성 (client)
12. `progress.index.md` 갱신 (client)

### 헬스체크
```text
--- healthcheck ---
area: server → client (cross-area)
mode: balanced
read: [server/tasks/task-06-test-posts.md, server/progress.index.md, client/tasks/task-02-page-routing.md, client/progress.index.md]
updated: [src/routes/posts.ts, src/app/posts/page.tsx, task files (both), progress files (both)]
notes: 영역 간 작업 전환
--- end ---
```

---

## 시나리오 4: 과거 기술 조사 참조

**사용자 요청**: "Drizzle ORM으로 복잡한 조인 쿼리를 작성해야 해"

### 워크플로
1. `@docs/server/tasks/` 목록 확인 → 해당 task 파일 읽기
2. `@docs/server/findings.index.md` 읽기
3. "Drizzle" 키워드로 `findings.003-drizzle-vs-prisma.md` 발견
4. `findings/findings.003-drizzle-vs-prisma.md` 읽기 (조인 전략 확인)
5. 쿼리 작성
6. `progress/progress.2026-02-15.md`에 "findings.003 참조하여 조인 쿼리 작성" 기록

### 헬스체크
```text
--- healthcheck ---
area: server
mode: balanced
read: [tasks/task-06-test-posts.md, findings.index.md, findings.003]
updated: [src/db/queries/posts.ts, progress.2026-02-15.md]
notes: 기존 findings 재활용
--- end ---
```

---

## 시나리오 5: Minimal 모드 사용

**사용자 요청**: "minimal 모드로 버튼 색상만 primary에서 secondary로 바꿔줘"

### 워크플로
1. `@docs/client/tasks/` 목록에서 관련 task 파일만 읽기 (minimal 모드)
2. 버튼 컴포넌트 파일 수정
3. progress 기록 생략 (너무 단순한 작업)

### 헬스체크
```text
--- healthcheck ---
area: client
mode: minimal
read: [tasks/task-01-component-library.md]
updated: [src/shared/ui/button.tsx]
notes: 단순 수정으로 progress 생략
--- end ---
```

---

## 시나리오 6: Deep 모드 사용

**사용자 요청**: "deep 모드로 전체 인증 아키텍처를 재설계해줘"

### 워크플로
1. `@docs/server/tasks/` 전체 목록 확인
2. 인증 관련 task 파일들 읽기
3. `@docs/server/findings.index.md` + `progress.index.md` 읽기
4. 최근 5개 findings 파일 모두 읽기 (인증 관련)
5. 최근 5개 progress 파일 읽기 (기존 시도 확인)
6. 아키텍처 설계
7. `findings/findings.010-auth-architecture-v2.md` 생성
8. progress 기록

### 헬스체크
```text
--- healthcheck ---
area: server
mode: deep
read: [tasks/ (전체 목록), findings.index.md, findings.001-007, progress.index.md, progress (recent 5)]
updated: [findings.010, findings.index.md, src/hooks/auth.hook.ts, progress.2026-02-15.md]
notes: 복잡한 아키텍처 결정으로 deep 모드 사용
--- end ---
```

---

## 시나리오 7: 새 Task 파일 생성

**사용자 요청**: "새로운 작업으로 이미지 업로드 기능을 추가해줘"

### 워크플로
1. `@docs/server/tasks/` 폴더 목록 확인
2. 최대 순번 확인 (예: task-09가 마지막)
3. `tasks/task-10-image-upload.md` 생성 (템플릿 기반)
4. 작업 항목, 선행 조건, 검증 기준 작성
5. progress 기록

### 헬스체크
```text
--- healthcheck ---
area: server
mode: balanced
read: [tasks/ (목록 확인)]
updated: [tasks/task-10-image-upload.md, progress.2026-02-15.md, progress.index.md]
notes: 새 task 파일 생성
--- end ---
```
