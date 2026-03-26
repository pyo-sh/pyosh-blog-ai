# [F-33c] Client 환경 변수 설정

> Client(Next.js) 환경 변수 분리 및 API URL 개선. 서버 사이드 fetch가 내부 URL을 사용하도록 변경한다.

## SPEC 참조

- `docs/specs/deploy-env.md` (섹션 5.3 Client 환경 변수)

## 상세 설계

### Client 환경 변수

| 변수 | 공개 범위 | 용도 |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | 브라우저 + 서버 | 브라우저에서 API 서버로의 요청 기본 URL |
| `API_URL` | 서버 전용 | Next.js 서버(미들웨어, RSC)에서 API 서버로의 내부 요청 URL |

### API URL 분리 이유

| 환경 | `NEXT_PUBLIC_API_URL` | `API_URL` |
|---|---|---|
| 로컬 개발 | `http://localhost:5500` | `http://localhost:5500` |
| 프로덕션 | `https://api.example.com` (외부) | `http://api-server:5500` (내부) |

브라우저는 외부 공개 URL로만 접근 가능하지만, Next.js 서버는 같은 네트워크 내부 URL을 사용할 수 있다. 이를 분리하면 불필요한 외부 라우팅을 방지하고 응답 속도를 개선할 수 있다.

### 개선 사항: serverFetch의 API_URL 사용

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

### env 파일 로딩

Next.js 내장 env 로딩 규칙을 따른다:

```
1. .env                  (공통)
2. .env.local             (로컬 오버라이드, .gitignore)
3. .env.development       (개발 환경)
4. .env.development.local (개발 로컬 오버라이드)
```

현재는 `.env.local` 단일 파일로 운영한다.

### .env.local.example 파일

`NEXT_PUBLIC_API_URL`과 `API_URL`.

```env
# 브라우저에서 API 서버로의 요청 URL
NEXT_PUBLIC_API_URL=http://localhost:5500

# Next.js 서버(RSC, middleware)에서 API 서버로의 내부 요청 URL
# 미설정 시 NEXT_PUBLIC_API_URL 폴백
API_URL=http://localhost:5500
```

## API 연동

없음. 환경 설정 인프라 스펙.

## 수용 기준

- [ ] Client `serverFetch()`가 `API_URL`을, `clientFetch()`가 `NEXT_PUBLIC_API_URL`을 사용한다
- [ ] `API_URL` 미설정 시 `NEXT_PUBLIC_API_URL`로 폴백한다
- [ ] `.env.local.example` 파일이 실제 필요 변수와 일치한다
- [ ] 프로덕션 환경에서 env 수동 주입으로 정상 동작한다

## 에지 케이스

| 케이스 | 처리 |
|---|---|
| API_URL 미설정 (Client) | `NEXT_PUBLIC_API_URL` 폴백 |
| 프로덕션에서 API_URL 미설정 (미들웨어) | `console.error` 출력 + 인증 거부로 대시보드 접근 차단 |

## 의존성

- Blocked by: 없음
- Blocks: 없음
