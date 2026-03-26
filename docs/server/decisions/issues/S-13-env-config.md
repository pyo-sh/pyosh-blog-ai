# Environment variable configuration

> 서버 환경 변수 Zod 스키마 검증, env 파일 로딩 순서, 레거시 정리, .env.example 관리

## SPEC 참조

- `docs/specs/deploy-env.md` > 5.1 환경 분리 전략, 5.2 Server 환경 변수, 5.4 레거시 정리, 5.5 .env.example, 5.6 Docker Compose

## 상세

### 5.1 환경 분리 전략

#### env 파일 로딩 순서 (Server)

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

### 5.4 레거시 정리

#### 삭제 대상

| 파일 | 이유 |
|---|---|
| `server/src/constants/env.ts` | Zod 기반 `shared/env.ts`로 완전 대체됨. 임포트 0건 |

`constants/node-env.ts`는 `NodeEnv` enum을 다른 파일에서도 사용하는지 확인 후, 미사용 시 함께 삭제한다.

#### 호환성 export 유지

`shared/env.ts`의 `export default env` (기존 코드 호환용)는 당분간 유지한다.

### 5.5 .env.example 파일 관리

Server `.env.example`:
- Zod 스키마의 모든 필수 변수 + 선택 변수(주석 표시)
- `BASE_URL`, `BLOG_TITLE`, `BLOG_DESCRIPTION` 포함

### 5.6 Docker Compose 환경

`tools/docker/docker-compose.yaml`에서 root `.env` 파일을 `env_file`로 참조한다.

Docker 환경 전용 변수:

| 변수 | 기본값 | 용도 |
|---|---|---|
| `TZ` | `Asia/Seoul` | 컨테이너 타임존 |
| `PLAYWRIGHT_BROWSERS_PATH` | `/opt/ms-playwright` | Playwright 브라우저 경로 (Dockerfile) |

### 에지 케이스

| 케이스 | 처리 |
|---|---|
| NODE_ENV 미설정 | `development` 기본값, `.env`만 로드 |
| 필수 변수 빈 문자열 | `.min(1)`로 차단 |
| SERVER_PORT에 문자열 | `.coerce.number()`로 변환 시도, 실패 시 검증 에러 |
| CLIENT_PORT = 0 | 포트 생략 (`:0` 미포함) |

## 수용 기준

- [ ] Server가 Zod 스키마 단일 체계로 env를 검증한다
- [ ] 레거시 `constants/env.ts`가 삭제되었다
- [ ] 필수 변수 누락 시 서버 시작이 차단되고 상세 에러가 출력된다
- [ ] `.env` -> `.env.{ENV_TARGET}.local` 순서로 오버라이드가 동작한다
- [ ] 파생 변수 `CLIENT_URL`이 올바르게 생성된다
- [ ] `CLIENT_PORT = 0`일 때 포트가 생략된다
- [ ] `.env.example` 파일이 실제 필요 변수와 일치한다
- [ ] Docker Compose 환경에서 root `.env` 기반으로 정상 동작한다
- [ ] frozen object로 export되어 런타임 변경이 불가하다

## 의존성

- Blocked by: 없음 (기반 기능)
- Blocks: S-14

## 참고

- 프로덕션 환경 변수는 호스팅 환경에서 수동 주입한다. `.env.production.local`은 로컬 테스트 전용이다.
- `constants/node-env.ts` 삭제 여부는 다른 파일에서의 사용 여부를 확인 후 결정한다.
- `shared/env.ts`의 `export default env`는 기존 코드 호환을 위해 당분간 유지한다.
