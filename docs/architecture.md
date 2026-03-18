# Architecture Overview

> pyosh-blog v1

**상태:** DRAFT
**최종 수정:** 2026-03-18

---

## 1. 프로젝트 개요

개인 블로그 플랫폼. 마크다운 기반 글 작성, 댓글/방명록, 관리 페이지를 제공한다.

- 개인 블로그이며 기술 블로그는 일부
- 대상 사용자: 관리자(1인), 블로그 방문자(비로그인)
- OAuth 로그인 사용자는 후속 버전에서 지원 (확장을 고려한 설계)
- v1 = 블로그가 정상 기능하는 상태로 배포될 때까지

---

## 2. 시스템 구성

```
┌──────────────┐              ┌──────────────┐              ┌─────────┐
│   Client     │────HTTP─────▶│   Server     │─────────────▶│  MySQL   │
│  Next.js 14  │              │  Fastify 5   │              │          │
└──────────────┘              └──────────────┘              └─────────┘
   별도 머신                     별도 머신                    서버 로컬
```

- Client와 Server는 별도 머신에서 운영. 서브도메인을 이용한 통신 가능
- 배포: 클라우드 서버(Oracle Cloud 등) 예정. 프론트는 Vercel 등으로 변경될 수 있음
- 파일 스토리지: 현재 로컬 파일시스템. DB에는 경로 string만 저장하여 외부 스토리지 전환 가능
- Redis, CDN 등 추가 인프라 없음 (개인 블로그 규모)

---

## 3. 기술 스택

### Client

| 영역 | 기술 | 비고 |
|---|---|---|
| 프레임워크 | Next.js 14 (App Router) | React 18 |
| 언어 | TypeScript 5.9 | |
| 스타일링 | TailwindCSS v4 | + @tailwindcss/typography |
| 데이터 페칭 | TanStack Query v5 | 서버 컴포넌트는 직접 fetch |
| 마크다운 렌더링 | unified + remark + rehype | 서버 사이드 |
| 코드 하이라이팅 | Shiki v4 | |
| 컴포넌트 확인 | Storybook | v1 포함 |
| 아키텍처 | FSD (Feature-Sliced Design) | |

### Server

| 영역 | 기술 | 비고 |
|---|---|---|
| 프레임워크 | Fastify 5 | |
| 언어 | TypeScript 5.9 | |
| DB | MySQL | mysql2 드라이버 |
| ORM | Drizzle ORM | + Drizzle Kit (마이그레이션) |
| 검증 | Zod | fastify-type-provider-zod |
| 인증 | Passport (Google, GitHub OAuth) | + argon2 (관리자 비밀번호) |
| 세션 | @fastify/session + cookie | |
| 보안 | helmet, CSRF, rate-limit, CORS | |
| 파일 업로드 | @fastify/multipart | 로컬 파일시스템 저장 |
| API 문서 | Swagger + Swagger UI | v1에서 세부화 예정 |
| 테스트 | Vitest | |

---

## 4. 설계 원칙

### 우선순위

| 순위 | 원칙 | 설명 |
|---|---|---|
| 1 | 보안 우선 | CSRF, rate limiting, 입력 검증, 인증/인가 분리 |
| 2 | 재사용성 | 코드, 기능, 환경의 재사용 (스토리지 추상화, 엔티티별 API 이중 제공 등) |
| 3 | 개발자 편의 | 디버깅 용이성, Swagger/Storybook 등 확인 도구 |

### 적용된 설계 결정

1. **FSD 아키텍처** - `app → widgets → features → entities → shared` 단방향 의존
2. **데이터 페칭 이원화**
   - 정적/읽기 전용: Server Component SSR (게시글, 카테고리, 태그, related posts)
   - 가변 데이터 (사용자 입력): SSR `initialData` + TanStack Query (댓글, 방명록, 검색)
   - Admin: TanStack Query only
3. **소프트 삭제** - 게시글 `deletedAt` 기반, 복원 가능
4. **스토리지 추상화** - DB에 경로 string만 저장, 백엔드 교체 가능
5. **서버 사이드 마크다운 렌더링** - 클라이언트 번들에 파서 미포함
6. **댓글 depth 제한** - 최대 1단계 (댓글 + 대댓글)
7. **API 계약 이중 관리** - `api-spec.md` (AI/개발 계약서) + Swagger (인간 확인용), 동기화 유지
8. **에러 가시성** - Public은 문제 예측 가능한 수준, 내부는 세부 발생 경로까지 확인 가능
9. **RESTful + admin prefix 분리** - 도메인 분리 가능한 구조

---

## 5. v1 기능 범위

### Public

| # | 기능 |
|---|---|
| 1 | 홈 - 글 목록 (페이지네이션) |
| 2 | 글 상세 (마크다운 렌더링, 코드 하이라이팅) |
| 3 | 카테고리별 글 목록 |
| 4 | 태그 목록 / 태그별 글 목록 |
| 5 | 인기 글 (7일/30일) |
| 6 | 댓글 (게스트 작성/삭제, 대댓글, 비밀글) |
| 7 | 방명록 (게스트 작성/삭제) |
| 8 | 조회수 기록 |
| 9 | 검색 |
| 10 | UX 기본 (404, 에러, 로딩, 빈 상태, Toast) |
| 11 | 스크롤 (맨 위로, TOC) |
| 12 | 다크 모드 + 반응형 |

### Admin

| # | 기능 |
|---|---|
| 13 | 관리자 로그인 |
| 14 | 대시보드 (통계 요약) |
| 15 | 글 관리 (목록, 필터, 삭제/복원) |
| 16 | 글 에디터 (마크다운 + 프리뷰) |
| 17 | 카테고리 관리 (트리, CRUD, 순서) |
| 18 | 에셋 라이브러리 (업로드, 갤러리, 삭제) |
| 19 | 댓글 관리 (목록, 비밀글 확인, 강제 삭제) |
| 20 | 방명록 관리 (목록, 강제 삭제) |

### SEO / 웹 표준

| # | 기능 |
|---|---|
| 21 | 메타태그 + OG + sitemap + RSS |
| 22 | robots.txt + Canonical URL |
| 23 | 구조화 데이터 (JSON-LD) |
| 24 | Favicon / Web Manifest |

### 접근성

| # | 기능 |
|---|---|
| 25 | 키보드 네비게이션 + 포커스 관리 |
| 26 | Skip to content |
| 27 | ARIA 속성 |

### 배포 준비

| # | 기능 |
|---|---|
| 28 | 환경 변수 분리 (dev/production) |
| 29 | 프로덕션 쿠키/CORS 설정 |
| 30 | 에러 모니터링 |
| 31 | Footer 콘텐츠 |

### 개발 도구

| # | 기능 |
|---|---|
| 32 | Swagger 세부화 (예시 데이터, 상세 설명) |
| 33 | Storybook 환경 구성 |

---

## 6. 비목표 (Non-goals)

v1에서 의도적으로 제외하는 항목. 스코프 관리를 위해 명시한다.

1. **OAuth 소셜 로그인** - 서버 구현 완료. 클라이언트 연동은 심사 절차 이후
2. **다국어 (i18n)** - 현 시점에서 고려하지 않음
3. **CDN / 외부 캐시 레이어** - 개인 블로그 규모에서 과도
4. **Redis** - 현재 서비스 규모에서 불필요. 필요 시 추가
5. **실시간 기능** - WebSocket, SSE 등 실시간 알림이나 라이브 댓글 업데이트 없음
6. **글 시리즈/연재** - 계획 없음
7. **뉴스레터/구독** - 계획 없음
8. **멀티 관리자** - 단일 관리자 계정. 관리자 사용자 관리 기능 없음

---

## 7. 후속 작업 (Post-v1)

1. **OAuth 소셜 로그인** (Google/GitHub) - 서버 구현 완료, 클라이언트 연동 + 심사
2. **외부 파일 스토리지** - 로컬 → S3 등으로 전환 (DB는 string이므로 준비됨)
3. **개인 서비스 추가** - 블로그 외 개인 용도 서비스 확장 가능성

---

## 참조

- API 명세: `docs/server/api-spec.md`
- 클라이언트 기능 명세: `docs/client/feature_spec.md`
- 기능별 상세 스펙: `docs/feature-index.md`
