# Server Findings Index

> Server(Fastify) 관련 기술 조사, 문제 해결, 인사이트 모음

## 📋 목차

| ID  | 제목                                                  | 날짜       | 태그                                     |
| --- | ----------------------------------------------------- | ---------- | ---------------------------------------- |
| 001 | 기술 스택 분석 (Express + TypeORM + 커스텀 Decorator) | 2026-02-06 | #tech-stack #express #typeorm #decorator |
| 002 | Phase 0 완료: Express 5.x 업그레이드                  | 2026-02-06 | #express5 #security #swagger-issue       |
| 003 | Server 마이그레이션 방향 결정 (Fastify 채택)          | 2026-02-09 | #fastify #zod #clean-architecture        |
| 004 | Phase S-0: Fastify + Vitest 환경 구축                 | 2026-02-09 | #fastify #vitest #vite-tsconfig-paths    |
| 005 | Phase S-1: Fastify 핵심 인프라 구축                   | 2026-02-09 | #fastify-plugin #typeorm #session        |
| 006 | Phase S-2: 인증 시스템 전환 (Fastify Passport)        | 2026-02-10 | #passport #oauth #fastify-session        |
| 007 | Phase S-3: User 도메인 마이그레이션 (Zod 이슈)        | 2026-02-10 | #zod #fastify-type-provider #json-schema |
| 008 | Phase S-5: 레거시 제거 (Express 완전 제거)            | 2026-02-10 | #express-removal #class-validator #mocha |
| 009 | Phase S-6: Drizzle ORM 마이그레이션                   | 2026-02-10 | #drizzle #typeorm-removal #session-store |
| 010 | Phase 2: Admin Auth Module (Argon2 + 세션 인증)       | 2026-02-10 | #admin-auth #argon2 #session #fastify-passport |
| 011 | Stats Service 설계 (Task 01)                          | 2026-02-16 | #stats #drizzle #fastify #anti-abuse |
| 012 | SEO XML Route 설계 (Sitemap + RSS)                    | 2026-02-16 | #seo #sitemap #rss #xml #fastify |
| 013 | Rate Limiting & CSRF 보호 전략                        | 2026-02-22 | #rate-limit #csrf #security #fastify |
| 014 | 게시글 검색 전략 (MySQL LIKE)                         | 2026-02-22 | #search #mysql #like #drizzle |

## 🔗 상세 문서

- [findings.001-tech-stack.md](./findings/findings.001-tech-stack.md) - 초기 기술 스택 분석
- [findings.002-phase0.md](./findings/findings.002-phase0.md) - Express 5 업그레이드
- [findings.003-migration-direction.md](./findings/findings.003-migration-direction.md) - Fastify 채택 결정
- [findings.004-phase-s0.md](./findings/findings.004-phase-s0.md) - Fastify 환경 구축
- [findings.005-phase-s1.md](./findings/findings.005-phase-s1.md) - 인프라 구축
- [findings.006-phase-s2.md](./findings/findings.006-phase-s2.md) - 인증 시스템
- [findings.007-phase-s3.md](./findings/findings.007-phase-s3.md) - User 도메인 + Zod 이슈
- [findings.008-phase-s5.md](./findings/findings.008-phase-s5.md) - 레거시 제거
- [findings.009-phase-s6.md](./findings/findings.009-phase-s6.md) - Drizzle ORM
- [findings.010-phase2-admin-auth.md](./findings/findings.010-phase2-admin-auth.md) - Admin Auth Module
- [findings.011-stats-service-design.md](./findings/findings.011-stats-service-design.md) - Stats Service 설계
- [findings.012-seo-sitemap-rss.md](./findings/findings.012-seo-sitemap-rss.md) - SEO XML Route 설계
- [findings.013-rate-limiting-csrf.md](./findings/findings.013-rate-limiting-csrf.md) - Rate Limiting & CSRF 보호 전략
- [findings.014-post-search-strategy.md](./findings/findings.014-post-search-strategy.md) - 게시글 검색 전략 (MySQL LIKE)

## 📊 요약

### 주요 성과

- **Express → Fastify 전환**: 2-3배 성능 향상
- **TypeORM → Drizzle 전환**: 80% 번들 크기 감소, 1.5-2배 쿼리 성능 향상
- **커스텀 프레임워크 제거**: 500 LOC 제거, 유지보수 부담 해소
- **의존성 감소**: 77개 → 43개 (44% 감소)
- **experimentalDecorators 제거**: TC39 표준 준수 완료
- **Mocha → Vitest**: 테스트 속도 향상, ESM 네이티브 지원

### 주요 이슈

- **fastify-type-provider-zod**: JSON Schema 변환 실패 → 수동 검증으로 우회
- **swagger-express-ts**: abandoned 패키지 → @fastify/swagger로 교체
- **Session Store**: TypeORM Store 제거 → 커스텀 Drizzle Store 구현

### 최종 기술 스택

- **프레임워크**: Fastify 5.x
- **ORM**: Drizzle ORM
- **검증**: Zod + drizzle-zod
- **테스트**: Vitest
- **인증**: @fastify/passport
- **세션**: @fastify/session + 커스텀 Drizzle Store
- **API 문서**: @fastify/swagger + @fastify/swagger-ui

### 코드 감소

- **총 LOC**: ~2,464 → ~1,200 (51% 감소)
- **core/**: 500 LOC → 0 LOC (100% 제거)
- **test/**: 600 LOC → 100 LOC (83% 감소)

## 🎯 교훈

1. **커스텀 프레임워크**: 초기엔 유연하나 장기적으로 유지보수 부담
2. **표준 준수**: TC39 표준 따르기가 미래 호환성에 유리
3. **경량 프레임워크**: 규모가 작을수록 Fastify > NestJS
4. **Drizzle ORM**: 타입 안전성 + 성능 + 번들 크기에서 우수
5. **Zod 통합**: drizzle-zod로 스키마 자동 생성 가능
