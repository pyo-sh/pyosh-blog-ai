# F-34: 프로덕션 쿠키/CORS 설정

**상태:** DRAFT
**최종 수정:** 2026-03-24

---

## 1. 개요

프로덕션 배포를 위한 보안 설정. 세션 쿠키 플래그 (dev/prod 분리), CORS origin 제한, CSRF 보호 범위 확대, CSP 헤더 (Next.js), Swagger 프로덕션 비활성화, OAuth 환경변수 비활성화를 설정한다.

## 2. 배경 및 동기

현재 구현 상태:

- 쿠키: `secure`만 조건부 설정. `httpOnly`, `sameSite` 미설정
- CORS: 단일 origin (`CLIENT_URL`), credentials 허용. methods/headers/max-age 미명시
- CSRF: `@fastify/csrf-protection` 등록되었으나 로그아웃 라우트에만 적용
- CSP: dev에서 설정, 프로덕션에서 비활성 (Swagger UI 호환)
- Swagger: dev/prod 구분 없이 항상 활성
- Helmet: HSTS가 `CLIENT_PROTOCOL === 'https'`로 조건부 적용
- OAuth: Google/GitHub 구현되어 있으나 v1에서 미사용

보안 위험:

- `httpOnly` 미설정 → XSS로 세션 쿠키 탈취 가능
- `sameSite` 미설정 → CSRF 공격에 취약
- CSRF 토큰이 대부분 라우트에서 검증되지 않음
- CSP 미적용 → 악성 스크립트 삽입 방어 없음

## 3. 목표

- 세션 쿠키에 dev/prod 별 보안 플래그를 적용한다
- CSRF 보호를 Admin 라우트 전체 + 사용자 상태 변경 라우트에 확대한다
- CSP를 Next.js에서 설정한다 (Fastify는 API 전용이므로 CSP 불필요)
- 프로덕션에서 Swagger를 비활성화한다
- OAuth를 환경변수로 비활성화한다

## 4. 비목표

- SSL 인증서 관리 (인프라 레벨)
- WAF (Web Application Firewall) 설정
- DDoS 방어
- 보안 감사/펜테스트

---

## 5. 상세 설계

### 5.1 세션 쿠키 설정

#### 환경별 설정

```typescript
const cookieConfig = {
  development: {
    secure: false,         // HTTP (dev는 HTTPS 없음)
    httpOnly: true,        // JS에서 접근 불가
    sameSite: 'lax' as const,       // dev에서 관대하게
    path: '/',
    maxAge: 24 * 60 * 60 * 1000,    // 24시간
  },
  production: {
    secure: true,          // HTTPS만
    httpOnly: true,        // JS에서 접근 불가
    sameSite: 'strict' as const,    // 외부 사이트에서 쿠키 미전송
    path: '/',
    maxAge: 24 * 60 * 60 * 1000,    // 24시간
  },
};

// session.ts에서 NODE_ENV에 따라 선택
const cookie = cookieConfig[env.NODE_ENV === 'production' ? 'production' : 'development'];
```

#### 플래그 설명

| 플래그 | 용도 |
|---|---|
| `httpOnly` | JavaScript (`document.cookie`)로 접근 불가 → XSS로 쿠키 탈취 방지 |
| `secure` | HTTPS 연결에서만 쿠키 전송 → 네트워크 도청 방지 |
| `sameSite: strict` | 외부 사이트에서의 요청에 쿠키 미포함 → CSRF 방지 |
| `sameSite: lax` | GET 리다이렉트에서는 쿠키 포함 → dev 호환성 |

#### dev에서 lax인 이유

`strict`도 localhost에서 동작하지만, 브라우저별 localhost 처리 차이와 개발 도구 호환성 문제를 피하기 위해 `lax` 사용. prod에서만 `strict` 적용.

### 5.2 CORS 설정

#### 환경별 설정

```typescript
// cors.ts
await fastify.register(cors, {
  origin: [env.CLIENT_URL],
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-CSRF-Token'],
  maxAge: env.NODE_ENV === 'production' ? 7200 : 0, // prod: 2시간 (Chrome 최대값), dev: 없음
});
```

| 설정 | 값 | 이유 |
|---|---|---|
| `origin` | `CLIENT_URL` 단일 | 허용된 프론트엔드만 |
| `credentials` | `true` | 세션 쿠키 포함 |
| `methods` | 명시적 나열 | 허용 메서드 제한 |
| `allowedHeaders` | 명시적 나열 | CSRF 토큰 헤더 포함 |
| `maxAge` | prod 24h, dev 0 | preflight 캐시 |

### 5.3 CSRF 보호 확대

#### 적용 범위

| 라우트 그룹 | 적용 방식 | 비고 |
|---|---|---|
| `/api/admin/*` (GET 제외) | 프리픽스 레벨 hook 일괄 적용 | 모든 Admin 상태 변경 |
| `POST /api/posts/:postId/comments` | 개별 route hook | 댓글 작성 |
| `DELETE /api/comments/:id` | 개별 route hook | 댓글 삭제 |
| `POST /api/guestbook` | 개별 route hook | 방명록 작성 |
| `DELETE /api/guestbook/:id` | 개별 route hook | 방명록 삭제 |
| `POST /api/assets/upload` | 이미 적용됨 | 유지 |
| GET 요청 전체 | 미적용 | 읽기 전용 |

#### Admin 일괄 적용

```typescript
fastify.register(async (adminRoutes) => {
  adminRoutes.addHook('onRequest', async (request, reply) => {
    if (request.method !== 'GET') {
      await fastify.csrfProtection(request, reply);
    }
  });

  adminRoutes.register(postAdminRoutes);
  adminRoutes.register(categoryAdminRoutes);
  adminRoutes.register(commentAdminRoutes);
  adminRoutes.register(guestbookAdminRoutes);
  adminRoutes.register(assetAdminRoutes);
  adminRoutes.register(settingsAdminRoutes);
}, { prefix: '/api/admin' });
```

#### CSRF 토큰 발급

기존 `GET /api/auth/csrf-token` 엔드포인트 유지. 클라이언트가 페이지 로드 시 토큰을 받아 이후 요청에 `X-CSRF-Token` 헤더로 포함.

### 5.4 CSP (Content Security Policy)

CSP는 **Next.js에서 설정**한다. Fastify는 API(JSON) 전용이므로 CSP 불필요.

#### Next.js 설정

```js
// next.config.js
async headers() {
  const isDev = process.env.NODE_ENV === 'development';
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || '';

  return [
    {
      source: '/(.*)',
      headers: [
        {
          key: 'Content-Security-Policy',
          value: [
            "default-src 'self'",
            isDev
              ? "img-src 'self' http: https: data: blob:"
              : "img-src 'self' https: data: blob:",
            "script-src 'self'",
            "style-src 'self' 'unsafe-inline'",
            "font-src 'self' https://fonts.gstatic.com",
            `connect-src 'self' ${apiUrl}`,
          ].join('; '),
        },
      ],
    },
  ];
}
```

#### Report-only 단계적 적용

초기 배포 시 `Content-Security-Policy-Report-Only` 헤더를 사용하여 차단 없이 위반 로그만 수집한다. 안정화 확인 후 실제 `Content-Security-Policy`로 전환한다.

```js
// 1단계: report-only (차단 없음, 위반만 브라우저 콘솔에 로깅)
{
  key: 'Content-Security-Policy-Report-Only',
  value: cspDirectives,
}

// 2단계: 안정화 확인 후 실제 차단으로 전환
{
  key: 'Content-Security-Policy',
  value: cspDirectives,
}
```

- report-only 모드에서 브라우저 콘솔에 `[Report Only]` 위반 로그 출력
- 정상 리소스가 차단되지 않으므로 서비스 영향 없음
- 위반 로그를 확인하여 디렉티브 조정 후 실제 차단으로 전환

#### CSP 디렉티브 설명

| 디렉티브 | 값 | 이유 |
|---|---|---|
| `default-src` | `'self'` | 기본 동일 출처만 |
| `img-src` | `'self' https: data: blob:` | Admin URL 입력, 마크다운 외부 이미지, 썸네일 blob 미리보기 |
| `script-src` | `'self'` | 인라인/외부 스크립트 차단 (XSS 방어) |
| `style-src` | `'self' 'unsafe-inline'` | Tailwind 인라인 스타일 허용 |
| `font-src` | `'self' fonts.gstatic.com` | Gothic A1 웹폰트 |
| `connect-src` | `'self' {API_URL}` | API 서버 연결 허용 |

dev에서 `img-src`에 `http:` 추가: Fastify 로컬 서버가 HTTP로 이미지 서빙.

#### Fastify Helmet 정리

```typescript
// helmet.ts
contentSecurityPolicy: false,  // Next.js가 담당
hsts: env.CLIENT_PROTOCOL === 'https',  // 기존 유지
// X-Frame-Options, X-Content-Type-Options 등 기본값 유지
```

### 5.5 Swagger 프로덕션 비활성화

```typescript
// app.ts
if (env.NODE_ENV !== 'production') {
  await fastify.register(swagger, { ... });
  await fastify.register(swaggerUi, { ... });
}
```

- 프로덕션에서 `/docs` 미노출
- API 스키마 정보 외부 노출 방지

### 5.6 OAuth 환경변수 비활성화

v1에서 OAuth를 사용하지 않으므로 환경변수로 비활성화.

```env
# .env.production
GOOGLE_CLIENT_ID=
GITHUB_CLIENT_ID=
```

```typescript
// passport.ts
if (env.GOOGLE_CLIENT_ID) {
  passport.use('google', new GoogleStrategy({ ... }));
}
if (env.GITHUB_CLIENT_ID) {
  passport.use('github', new GitHubStrategy({ ... }));
}
```

- 환경변수가 비어있으면 해당 전략 미등록, OAuth 라우트 미활성
- 코드 삭제 불필요 (나중에 환경변수만 채우면 활성화)
- `SameSite: strict` 안전하게 사용 가능 (외부 리다이렉트 없음)

### 5.7 보안 설정 요약

| 항목 | Development | Production |
|---|---|---|
| 쿠키 `secure` | false | true |
| 쿠키 `httpOnly` | true | true |
| 쿠키 `sameSite` | lax | strict |
| CORS origin | `CLIENT_URL` | `CLIENT_URL` |
| CORS maxAge | 0 | 7200 (Chrome 최대) |
| CSRF | 적용 | 적용 |
| CSP `img-src` | `http: https: data: blob:` | `https: data: blob:` |
| HSTS | false | true |
| Swagger | 활성 | 비활성 |
| OAuth | 환경변수로 on/off | 비활성 (v1) |

---

## 6. API 연동

| 메서드 | 경로 | 용도 | 변경 사항 |
|---|---|---|---|
| GET | `/api/auth/csrf-token` | CSRF 토큰 발급 | 기존 유지 |

### 서버 변경 필요사항

| 항목 | 설명 |
|---|---|
| `session.ts` | 쿠키 설정 dev/prod 분리 |
| `cors.ts` | methods, allowedHeaders, maxAge 명시 |
| Admin 라우트 | CSRF hook 일괄 적용 |
| 공개 상태 변경 라우트 | CSRF hook 개별 적용 |
| `helmet.ts` | CSP 제거 (Next.js 담당) |
| `app.ts` | Swagger 프로덕션 조건부 등록 |
| `passport.ts` | OAuth 전략 조건부 등록 |

### 클라이언트 변경 필요사항

| 항목 | 설명 |
|---|---|
| `next.config.js` | CSP 헤더 설정 (dev/prod 분리) |

## 7. 수용 기준

- [ ] 프로덕션 쿠키에 `httpOnly`, `secure`, `sameSite: strict`가 설정된다
- [ ] dev 쿠키에 `httpOnly`, `sameSite: lax`가 설정된다
- [ ] CORS에 허용 methods, headers, maxAge가 명시된다
- [ ] Admin 라우트 전체에서 GET 제외 CSRF 검증이 동작한다
- [ ] 댓글/방명록 작성/삭제에서 CSRF 검증이 동작한다
- [ ] CSRF 토큰 없이 POST 요청 시 403이 반환된다
- [ ] Next.js에서 CSP 헤더가 응답에 포함된다
- [ ] 초기 배포 시 `Content-Security-Policy-Report-Only`로 위반 로그만 수집한다
- [ ] 안정화 후 `Content-Security-Policy`로 전환하여 실제 차단한다
- [ ] 프로덕션에서 외부 HTTPS 이미지가 정상 로드된다
- [ ] 프로덕션에서 Swagger UI (`/docs`)에 접근할 수 없다
- [ ] OAuth 환경변수가 비어있으면 OAuth 라우트가 등록되지 않는다
- [ ] HSTS 헤더가 HTTPS 환경에서만 활성화된다

## 8. 에지 케이스

| 케이스 | 처리 |
|---|---|
| CSRF 토큰 만료 | 401 → 클라이언트에서 토큰 재발급 후 재시도 |
| CSP가 정상 리소스를 차단 | 브라우저 콘솔에서 차단 로그 확인 후 디렉티브 조정 |
| 외부 HTTP 이미지 (prod) | CSP에 의해 차단 → Admin에게 HTTPS URL 사용 안내 |
| OAuth 환경변수 부분 설정 (ID만, Secret 없음) | 서버 startup 시 Zod 검증 실패 → exit(1) |
| dev에서 CSRF 토큰 없이 테스트 | CSRF는 test 환경에서 비활성 (기존 동작 유지) |

## 9. 의존성

- F-33 환경 변수 분리 (NODE_ENV, CLIENT_PROTOCOL 등)

## 10. 미해결 사항

없음. 모든 사항 확정됨.
