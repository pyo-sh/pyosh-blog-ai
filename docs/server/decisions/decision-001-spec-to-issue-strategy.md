# SPEC 기반 Server Issue 생성 전략

## Metadata

- **Date**: 2026-03-26
- **Status**: draft
- **Related**: `docs/server/api-spec.md`, `docs/specs/deploy-*.md`, `docs/server/specs/swagger-docs.md`

## Background

Server repo(`pyo-sh/pyosh-blog-be`)의 SPEC을 GitHub Issue로 변환한다. SPEC이 개발 완료의 기준이며, 기존 구현은 참고만 한다. 각 Issue는 AI가 해당 이슈만 보고 독립적으로 개발할 수 있는 최소 단위로 구성한다.

Server의 SPEC 소스는 3가지이다:

| 소스 | 파일 | 성격 |
|---|---|---|
| API 명세 | `docs/server/api-spec.md` | 전체 API 엔드포인트 정의 (단일 파일) |
| 개별 feature spec | `docs/server/specs/swagger-docs.md` | F-37 Swagger 세부화 |
| 공유 deployment spec | `docs/specs/deploy-env.md`, `deploy-security.md`, `deploy-monitoring.md` | F-33, F-34, F-35의 server 해당 부분 |

Client와 달리 개별 spec 파일이 1개뿐이므로, `api-spec.md`를 리소스 그룹 단위로 분해하여 Issue를 생성한다.

## Decision

### 원칙

1. **SPEC이 권위**: 기존 코드는 참고만 하며, SPEC 기준으로 재구현한다
2. **최소 단위**: AI 에이전트가 단일 세션에서 완료할 수 있는 범위
3. **자기 완결**: 각 Issue는 해당 리소스의 schema + service + route를 모두 포함한다
4. **별도 Issue**: 공유 spec(F-33, F-34, F-35)의 server 부분은 server repo에 별도 Issue로 생성한다

### Issue 분해 기준

`api-spec.md`를 리소스 그룹 단위로 분해한다. 같은 리소스의 public/admin API는 service layer를 공유하므로 하나의 Issue로 합친다.

### Issue 목록

#### Foundation (기반)

| # | Issue 제목 | 범위 | SPEC 소스 |
|---|---|---|---|
| S-01 | App bootstrap + health check | Fastify 설정, 플러그인(cors, helmet, session, cookie, multipart), 전역 에러 핸들러, health check 4개 엔드포인트 | api-spec.md > 에러 응답 형식, Health check |
| S-02 | DB schema + migrations | Drizzle ORM 스키마 13개 테이블, 마이그레이션 설정 | api-spec.md > DB 스키마 요약 |
| S-03 | Auth system | Admin login/logout, 세션 관리, CSRF 토큰, OAuth 라우트, rate limiting, requireAdmin/requireAuth/optionalAuth hooks | api-spec.md > 인증 방식, CSRF 보호, Rate limiting, Auth |

#### Core API (핵심 기능)

| # | Issue 제목 | 엔드포인트 수 | SPEC 소스 |
|---|---|---|---|
| S-04 | Posts API | 11 (public 3 + admin 8) | api-spec.md > Posts |
| S-05 | Comments API | 8 (public 3 + admin 5) | api-spec.md > Comments |
| S-06 | Guestbook + Settings API | 8 (public 3 + admin 3 + settings 2) | api-spec.md > Guestbook, Settings |
| S-07 | Assets API | 5 (admin only) | api-spec.md > Assets |
| S-08 | Categories API | 5 (public 1 + admin 4) | api-spec.md > Categories |
| S-09 | Tags API | 1 (public) | api-spec.md > Tags |
| S-10 | Stats API | 4 (public 3 + admin 1) | api-spec.md > Stats |
| S-11 | User API | 3 (OAuth profile) | api-spec.md > User |
| S-12 | SEO endpoints | 2 (sitemap.xml, rss.xml) | api-spec.md > SEO |

#### Enhancement (강화)

| # | Issue 제목 | SPEC 소스 | Feature # |
|---|---|---|---|
| S-13 | Environment variable configuration | `docs/specs/deploy-env.md` > 5.2, 5.4 (server 부분) | F-33 |
| S-14 | Production security settings | `docs/specs/deploy-security.md` > 5.1~5.3, 5.5~5.6 (server 부분) | F-34 |
| S-15 | Logging and error management | `docs/specs/deploy-monitoring.md` > 5.1~5.3, 5.5 (server 부분) | F-35 |
| S-16 | Swagger documentation | `docs/server/specs/swagger-docs.md` | F-37 |

**총 16개 Issue**

### 의존성 순서

```
Layer 0 (foundation - 병렬 가능)
├── S-01  App bootstrap + health check
├── S-02  DB schema + migrations
└── S-13  Env configuration (F-33)

Layer 1 (auth - S-01, S-02 완료 후)
└── S-03  Auth system

Layer 2 (core API - S-03 완료 후, 서로 병렬 가능)
├── S-04  Posts API
├── S-05  Comments API        ← S-04 (postId FK)
├── S-06  Guestbook + Settings API
├── S-07  Assets API
├── S-08  Categories API
├── S-09  Tags API
├── S-10  Stats API           ← S-04 (postId FK)
├── S-11  User API
└── S-12  SEO                 ← S-04, S-08 (posts, categories 데이터)

Layer 3 (enhancement - core 완료 후)
├── S-14  Production security  ← S-03 (auth hooks 기반)
├── S-15  Logging/error        ← S-01 (error handler 기반)
└── S-16  Swagger docs         ← 모든 route 완료 후
```

### Issue 템플릿

```markdown
## 목표

{1줄 요약}

## SPEC 참조

- 전체: `docs/server/api-spec.md` > {섹션명}
- (해당 시) 개별 spec: `docs/server/specs/{file}.md` 또는 `docs/specs/{file}.md`

## 엔드포인트

| Method | Path | Auth | 설명 |
|---|---|---|---|
| ... | ... | ... | ... |

## 요청/응답 스키마

{api-spec.md에서 해당 리소스의 스키마 전문 인용}

## 수용 기준

- [ ] {spec에서 추출한 수용 기준}
- [ ] ...

## 의존성

- Blocked by: {선행 Issue 번호}
- Blocks: {후행 Issue 번호}

## 참고

- CSRF 적용 대상: {해당 시}
- Rate limiting: {해당 시}
- Soft delete 지원: {해당 시}
```

### 라벨

| 라벨 | 용도 |
|---|---|
| `spec` | SPEC 기반 재구현 Issue 공통 |
| `layer:foundation` | S-01 ~ S-03, S-13 |
| `layer:core` | S-04 ~ S-12 |
| `layer:enhancement` | S-14 ~ S-16 |

### Issue 본문에 포함할 SPEC 내용

각 Issue 본문에 `api-spec.md`의 해당 섹션을 **전문 인용**한다. AI 에이전트가 Issue만 보고 개발할 수 있어야 하므로, 외부 파일 참조가 아닌 inline으로 SPEC을 포함한다.

- S-01 ~ S-12: `api-spec.md`에서 해당 리소스 섹션 전체
- S-13 ~ S-15: 공유 spec 파일에서 server 해당 섹션만 발췌
- S-16: `swagger-docs.md` 전문

## Consequences

- `api-spec.md`의 모든 엔드포인트가 16개 Issue로 빠짐없이 커버된다
- 각 Issue는 schema + service + route를 포함하는 자기 완결 단위이다
- Foundation → Auth → Core → Enhancement 순서로 개발 가능하다
- Core API Issue 간에는 FK 의존성 외에는 병렬 개발이 가능하다
