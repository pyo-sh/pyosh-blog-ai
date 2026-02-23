# 작업 예시

## 시나리오 1: Client 컴포넌트 개발 후 기록

**GitHub Issue**: `#42 - 블로그 포스트 카드 컴포넌트 개발`

### 워크플로
1. `@docs/client/progress.index.md` 읽기 (최근 작업 확인)
2. `@docs/client/findings.index.md` 읽기 (TailwindCSS 관련 검색)
3. `findings/findings.002-tailwind-v4-tokens.md` 선택적 읽기
4. `@client/CLAUDE.md`에서 Next.js/TailwindCSS 규칙 확인
5. `src/shared/ui/post-card.tsx` 생성
6. `progress/progress.2026-02-15.md` 생성 (상세 로그, `#42` 참조)
7. `progress.index.md`에 한줄 요약 추가

---

## 시나리오 2: Server API 개발 + 새 기술 조사

**GitHub Issue**: `#55 - 포스트 목록 조회 API 구현`

### 워크플로
1. `@docs/server/findings.index.md` 읽기 (페이지네이션 관련 없음 확인)
2. `@server/CLAUDE.md`에서 Fastify/Drizzle 규칙 확인
3. 페이지네이션 전략 조사 (cursor-based vs offset-based)
4. `findings/findings.004-pagination-strategy.md` 생성
5. `findings.index.md`에 항목 추가
6. `src/routes/posts.ts`에 GET /posts 라우트 추가
7. `progress/progress.2026-02-15.md` 생성 (`#55` 참조)
8. `progress.index.md`에 한줄 요약 추가

---

## 시나리오 3: Decision 작성

**GitHub Issue**: `#78 - 이미지 스토리지 전략 결정`

### 워크플로
1. `@docs/server/decisions.index.md` 읽기
2. 기존 decisions 확인 (관련 결정 있는지)
3. S3 vs Cloudflare R2 vs 로컬 스토리지 조사
4. `decisions/decision-003-image-storage.md` 생성 (상태: draft)
   - 옵션 비교, AI 제안 포함
   - 최종 결정은 사용자 확인 대기
5. `decisions.index.md`에 항목 추가
6. 사용자에게 결정 요청
7. 사용자 확인 후 상태를 `accepted`로 변경

---

## 시나리오 4: 영역 간 작업 전환

**GitHub Issue**: `#60 - 포스트 목록 API + 페이지 구현`

### 워크플로

#### Part 1: Server 작업
1. `@docs/server/progress.index.md`, `findings.index.md` 읽기
2. API 구현
3. `progress/progress.2026-02-15.md` 생성 (server)
4. `progress.index.md` 갱신 (server)

#### Part 2: Client 작업
5. `@docs/client/progress.index.md`, `findings.index.md` 읽기
6. 페이지 구현
7. `progress/progress.2026-02-15.md` 생성 (client)
8. `progress.index.md` 갱신 (client)

---

## 시나리오 5: 과거 기술 조사 참조

**GitHub Issue**: `#70 - 복잡한 조인 쿼리 최적화`

### 워크플로
1. `@docs/server/findings.index.md` 읽기
2. "Drizzle" 키워드로 `findings.003-drizzle-vs-prisma.md` 발견
3. `findings/findings.003-drizzle-vs-prisma.md` 읽기 (조인 전략 확인)
4. 쿼리 작성
5. `progress/progress.2026-02-15.md`에 "findings.003 참조하여 조인 쿼리 작성 (#70)" 기록

---

## 시나리오 6: Deep 모드 — 아키텍처 재설계

**GitHub Issue**: `#90 - 인증 아키텍처 재설계`

### 워크플로
1. `@docs/server/findings.index.md` + `progress.index.md` + `decisions.index.md` 읽기
2. 최근 5개 findings 파일 읽기 (인증 관련)
3. 기존 decisions 확인
4. 아키텍처 설계
5. `decisions/decision-005-auth-v2.md` 생성 (draft)
6. `findings/findings.010-auth-architecture-v2.md` 생성
7. progress 기록
8. 사용자에게 decision 승인 요청
