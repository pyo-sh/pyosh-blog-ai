# Client Progress Index

> Client(Next.js) 진행 상황 요약

## 📅 타임라인

| 날짜       | 주요 작업                            | 상태 |
| ---------- | ------------------------------------ | ---- |
| 2026-03-14 | #26 Public Post API functions PR #131 머지, #32 Pagination 공통 컴포넌트 PR #128 머지, #30 PostContent + PostNavigation PR #130 머지 | ✅   |
| 2026-03-09 | #24 PR #127 리뷰 코멘트 대응 (processor 모듈화, sanitizeSchema 코멘트), #29 Category entity PR #129 머지 | ✅   |
| 2026-03-08 | #24 마크다운 렌더링 유틸리티 (shiki), #29 Category entity 타입 + API, #30 PostContent + PostNavigation 컴포넌트 | ✅   |
| 2026-03-07 | #25 Post entity - PostNavigation 타입 추가 | ✅   |
| 2026-03-06 | #46 Admin 레이아웃 (사이드바), #50 Post CRUD API, #42 Stat entity, #31 마크다운 렌더링 의존성 설치, #23 PaginatedResponse meta.total 수정 | ✅   |
| 2026-03-04 | #34 CSRF 토큰 유틸리티 + mutation helper, #38 Auth entity types + API | ✅   |
| 2026-02-23 | #4 API 클라이언트 설정 (fetch wrapper + TanStack Query) | ✅   |
| 2026-02-06 | 기술 스택 분석 & Phase 0 (보안 패치) | ✅   |
| 2026-02-07 | ESLint 9 & Phase A (TailwindCSS v4)  | ✅   |
| 2026-02-08 | Phase D, E (Component 경계 & 테마)   | ✅   |
| 2026-02-09 | FSD 마이그레이션 & Emotion 제거 완성 | ✅   |

## 🔗 상세 문서

- [progress.2026-03-14.md](./progress/progress.2026-03-14.md) - #26 Public Post API functions PR #131 머지, #32 Pagination 공통 컴포넌트 PR #128 머지, #30 PostContent + PostNavigation PR #130 머지
- [progress.2026-03-09.md](./progress/progress.2026-03-09.md) - #24 PR #127 리뷰 코멘트 대응, #29 Category entity PR #129 머지
- [progress.2026-03-08.md](./progress/progress.2026-03-08.md) - #24 마크다운 렌더링 유틸리티 (shiki), #29 Category entity 타입 + API, #30 PostContent + PostNavigation 컴포넌트
- [progress.2026-03-07.md](./progress/progress.2026-03-07.md) - #25 Post entity - PostNavigation 타입 추가
- [progress.2026-03-06.md](./progress/progress.2026-03-06.md) - #46 Admin 레이아웃 (사이드바), #50 Post CRUD API, #42 Stat entity, #31 마크다운 렌더링 의존성 설치, #23 PaginatedResponse meta.total 수정
- [progress.2026-03-04.md](./progress/progress.2026-03-04.md) - #34 CSRF 토큰 유틸리티 + mutation helper, #38 Auth entity types + API
- [progress.2026-02-23.md](./progress/progress.2026-02-23.md) - #4 API 클라이언트 설정
- [progress.2026-02-06.md](./progress/progress.2026-02-06.md) - 기술 스택 분석 & Phase 0
- [progress.2026-02-07.md](./progress/progress.2026-02-07.md) - ESLint 9 & Phase A
- [progress.2026-02-08.md](./progress/progress.2026-02-08.md) - Phase D & E
- [progress.2026-02-09.md](./progress/progress.2026-02-09.md) - FSD 완성

## 📊 최종 성과

### 기술 스택 전환

- **Pages Router → App Router** 완료
- **Emotion → TailwindCSS v4** 완료
- **ESLint 8 → ESLint 9 Flat Config** 완료
- **TypeScript 4.9 → 5.9** 완료

### 보안 & 품질

- **취약점**: 20개 → 2개 (90% 감소)
- **"use client"**: 20+개 → 8개 (최소화)
- **타입 오류**: 4개 → 0개

### 구조 개선

- **FSD 구조** 전환 완료
- **레거시 제거**: pages/, styles/, components/ 삭제
- **CSS 통합**: theme.css 중심 구조
