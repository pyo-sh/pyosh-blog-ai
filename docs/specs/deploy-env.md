# F-33: 환경 변수 분리 (dev/production)

**상태:** DRAFT
**최종 수정:** 2026-03-20

---

## 1. 개요

개발/프로덕션/테스트 환경별 환경 변수 분리 전략을 정의한다. Server(Fastify)는 Zod 기반 검증, Client(Next.js)는 Next.js 내장 env 로딩을 사용한다. 레거시 env 시스템을 정리하고, 서버-클라이언트 간 API URL 사용을 개선한다.

## 2. 배경 및 동기

- 환경별 설정(DB, OAuth, API URL 등)이 다르므로 분리 관리가 필수
- 프로덕션 환경 변수는 수동 주입하되, 프로덕션 환경을 로컬에서 테스트할 수 있어야 함
- 레거시 `constants/env.ts`가 미사용 상태로 잔존하여 혼란 유발
- Client의 `serverFetch()`가 브라우저용 `NEXT_PUBLIC_API_URL`을 사용하고 있어, 프로덕션 배포 시 불필요한 외부 라우팅 발생 가능

## 3. 목표

- 환경별 `.env` 파일 분리 전략을 확립한다
- Server env 검증이 Zod 스키마 단일 체계로 동작하도록 레거시를 정리한다
- Client의 서버 사이드 fetch가 내부 URL(`API_URL`)을 사용하도록 개선한다
- 각 repo의 `.env.example`이 실제 필요 변수와 동기화되도록 한다
- 향후 개발 시 이 문서만으로 env 설정을 완료할 수 있도록 한다

## 4. 비목표

- 환경 변수 암호화 / Vault 연동
- CI/CD 파이프라인 env 주입 자동화
- Client 측 env 런타임 검증 (빌드 타임 인라인으로 충분)

---

## 5. 상세 설계

### 5.1 환경 분리 전략

#### env 파일 로딩 순서

**Server (Fastify):**

```
1. .env                         (공통 기본값)
2. .env.{ENV_TARGET}.local      (환경별 오버라이드)
```

| NODE_ENV | ENV_TARGET | 오버라이드 파일 |
|---|---|---|
| 미설정 | - | `.env`만 로드 |
| `development` | development | `.env.development.local` |
| `production` | production | `.env.production.local` |
| `test` | test | `.env.test` |

**Client (Next.js):**

Next.js 내장 env 로딩 규칙을 따른다:

```
1. .env                  (공통)
2. .env.local             (로컬 오버라이드, .gitignore)
3. .env.development       (개발 환경)
4. .env.development.local (개발 로컬 오버라이드)
```

현재는 `.env.local` 단일 파일로 운영한다.

#### 프로덕션 env 주입

프로덕션 환경 변수는 호스팅 환경에서 수동 주입한다. `.env.production.local` 파일은 로컬에서 프로덕션 설정을 테스트할 때만 사용한다.

### 5.2 Server 환경 변수

#### Zod 스키마 기반 검증

서버 시작 시 `src/shared/env.ts`에서 즉시 실행된다. 검증 실패 시 상세 에러를 출력하고 `process.exit(1)`로 서버 시작을 차단한다.

```
서버 시작
  └─ loadEnvFiles()        → .env + .env.{ENV}.local 로드
  └─ envSchema.parse()     → Zod 검증
       ├─ 성공 → frozen object export
       └─ 실패 → 에러 출력 + process.exit(1)
```

#### 변수 목록

| 변수 | 타입 | 필수 | 기본값 | 용도 |
|---|---|---|---|---|
| `NODE_ENV` | enum | 선택 | `development` | 환경 구분 |
| `SERVER_PORT` | number (양의 정수) | 필수 | - | 서버 포트 |
| `CLIENT_PROTOCOL` | string | 필수 | - | 클라이언트 프로토콜 (http/https) |
| `CLIENT_HOST` | string | 필수 | - | 클라이언트 호스트 |
| `CLIENT_PORT` | number (0 이상) | 선택 | `0` | 클라이언트 포트 (0이면 생략) |
| `BASE_URL` | url | 선택 | `CLIENT_URL` 파생 | RSS 피드 기본 URL |
| `BLOG_TITLE` | string | 선택 | `pyosh blog` | RSS 채널 제목 |
| `BLOG_DESCRIPTION` | string | 선택 | `Pyosh 개발 블로그의 최신 글을 제공합니다.` | RSS 채널 설명 |
| `DB_HOST` | string | 필수 | - | MySQL 호스트 |
| `DB_PORT` | number (양의 정수) | 필수 | - | MySQL 포트 |
| `DB_USER` | string | 필수 | - | MySQL 사용자 |
| `DB_PSWD` | string | 필수 | - | MySQL 비밀번호 |
| `DB_DTBS` | string | 필수 | - | MySQL 데이터베이스명 |
| `SESSION_SECRET` | string | 필수 | - | 세션 암호화 키 |
| `LOGIN_SUCCESS_PATH` | string | 필수 | - | OAuth 성공 리다이렉트 경로 |
| `LOGIN_FAILURE_PATH` | string | 필수 | - | OAuth 실패 리다이렉트 경로 |
| `GOOGLE_CLIENT_ID` | string | 필수 | - | Google OAuth 클라이언트 ID |
| `GOOGLE_CLIENT_SECRET` | string | 필수 | - | Google OAuth 시크릿 |
| `GITHUB_CLIENT_ID` | string | 필수 | - | GitHub OAuth 클라이언트 ID |
| `GITHUB_CLIENT_SECRET` | string | 필수 | - | GitHub OAuth 시크릿 |

#### 파생 변수 (자동 생성)

| 변수 | 생성 로직 | 용도 |
|---|---|---|
| `CLIENT_URL` | `new URL(${CLIENT_PROTOCOL}://${CLIENT_HOST}:${CLIENT_PORT}).origin` | CORS, OAuth 리다이렉트, SSE |
| `BASE_URL` | `BASE_URL` 지정 시 해당 값, 미지정 시 `CLIENT_URL` | RSS 피드 링크 기본 URL |

#### 코드 내 추가 환경 변수 (스키마 외)

| 변수 | 사용처 | 비고 |
|---|---|---|
| `APP_VERSION` | `health.service.ts` | `npm_package_version` 폴백 |
| `UPLOAD_DIR` | `file-storage.service.ts` | 기본값 `./uploads` |

이 변수들은 Zod 스키마에 포함하지 않고, 사용처에서 직접 `process.env`로 읽되 기본값을 제공한다.

### 5.3 Client 환경 변수

| 변수 | 공개 범위 | 용도 |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | 브라우저 + 서버 | 브라우저에서 API 서버로의 요청 기본 URL |
| `API_URL` | 서버 전용 | Next.js 서버(미들웨어, RSC)에서 API 서버로의 내부 요청 URL |

#### API URL 분리 이유

| 환경 | `NEXT_PUBLIC_API_URL` | `API_URL` |
|---|---|---|
| 로컬 개발 | `http://localhost:5500` | `http://localhost:5500` |
| 프로덕션 | `https://api.example.com` (외부) | `http://api-server:5500` (내부) |

브라우저는 외부 공개 URL로만 접근 가능하지만, Next.js 서버는 같은 네트워크 내부 URL을 사용할 수 있다. 이를 분리하면 불필요한 외부 라우팅을 방지하고 응답 속도를 개선할 수 있다.

#### 개선 사항: serverFetch의 API_URL 사용

현재 `serverFetch()`가 `NEXT_PUBLIC_API_URL`을 사용하고 있다. 서버 사이드에서 실행되는 `serverFetch()`는 `API_URL`을 사용하도록 변경한다.

**변경 전:**

```typescript
// src/shared/api/client.ts
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:5500";

// serverFetch, clientFetch 모두 같은 API_URL 사용
```

**변경 후:**

```typescript
// src/shared/api/client.ts
const PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:5500";
const INTERNAL_API_URL = process.env.API_URL ?? PUBLIC_API_URL;

// clientFetch: PUBLIC_API_URL (브라우저 → API)
// serverFetch: INTERNAL_API_URL (Next.js 서버 → API)
```

### 5.4 레거시 정리

#### 삭제 대상

| 파일 | 이유 |
|---|---|
| `server/src/constants/env.ts` | Zod 기반 `shared/env.ts`로 완전 대체됨. 임포트 0건 |

`constants/node-env.ts`는 `NodeEnv` enum을 다른 파일에서도 사용하는지 확인 후, 미사용 시 함께 삭제한다.

#### 호환성 export 유지

`shared/env.ts`의 `export default env` (기존 코드 호환용)는 당분간 유지한다.

### 5.5 .env.example 파일 관리

각 repo의 example 파일은 실제 필요 변수와 동기화를 유지한다.

**Root `.env.example`:**

Docker Compose가 참조하는 공통 변수.

**Server `.env.example`:**

Zod 스키마의 모든 필수 변수 + 선택 변수(주석 표시). `BASE_URL`, `BLOG_TITLE`, `BLOG_DESCRIPTION` 포함.

**Client `.env.local.example`:**

`NEXT_PUBLIC_API_URL`과 `API_URL`.

### 5.6 Docker Compose 환경

`tools/docker/docker-compose.yaml`에서 root `.env` 파일을 `env_file`로 참조한다. Docker 환경 전용 변수:

| 변수 | 기본값 | 용도 |
|---|---|---|
| `TZ` | `Asia/Seoul` | 컨테이너 타임존 |
| `PLAYWRIGHT_BROWSERS_PATH` | `/opt/ms-playwright` | Playwright 브라우저 경로 (Dockerfile) |

## 6. API 연동

없음. 환경 설정 인프라 스펙.

## 7. 수용 기준

- [ ] Server가 Zod 스키마 단일 체계로 env를 검증한다
- [ ] 레거시 `constants/env.ts`가 삭제되었다
- [ ] 필수 변수 누락 시 서버 시작이 차단되고 상세 에러가 출력된다
- [ ] `.env` → `.env.{ENV_TARGET}.local` 순서로 오버라이드가 동작한다
- [ ] Client `serverFetch()`가 `API_URL`을, `clientFetch()`가 `NEXT_PUBLIC_API_URL`을 사용한다
- [ ] 각 repo의 `.env.example` 파일이 실제 필요 변수와 일치한다
- [ ] 프로덕션 환경에서 env 수동 주입으로 정상 동작한다
- [ ] Docker Compose 환경에서 root `.env` 기반으로 정상 동작한다

## 8. 에지 케이스

| 케이스 | 처리 |
|---|---|
| NODE_ENV 미설정 | `development` 기본값, `.env`만 로드 |
| 필수 변수 빈 문자열 | `.min(1)`로 차단 |
| SERVER_PORT에 문자열 | `.coerce.number()`로 변환 시도, 실패 시 검증 에러 |
| CLIENT_PORT = 0 | 포트 생략 (`:0` 미포함) |
| API_URL 미설정 (Client) | `NEXT_PUBLIC_API_URL` 폴백 |
| 프로덕션에서 API_URL 미설정 (미들웨어) | `console.error` 출력 + 인증 거부로 대시보드 접근 차단 |

## 9. 의존성

- 없음 (기반 기능)

## 10. 미해결 사항

- `constants/node-env.ts`가 레거시 env 외 다른 곳에서 사용되는지 확인 후 삭제 여부 결정
