# Production security settings

> 세션 쿠키 보안 플래그, CORS 설정, CSRF 확대, Swagger 프로덕션 비활성화, OAuth 환경변수 비활성화

## SPEC 참조

- `docs/specs/deploy-security.md` > 5.1 세션 쿠키 설정, 5.2 CORS 설정, 5.3 CSRF 보호 확대, 5.5 Swagger 프로덕션 비활성화, 5.6 OAuth 환경변수 비활성화

## 상세

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
| `httpOnly` | JavaScript (`document.cookie`)로 접근 불가 - XSS로 쿠키 탈취 방지 |
| `secure` | HTTPS 연결에서만 쿠키 전송 - 네트워크 도청 방지 |
| `sameSite: strict` | 외부 사이트에서의 요청에 쿠키 미포함 - CSRF 방지 |
| `sameSite: lax` | GET 리다이렉트에서는 쿠키 포함 - dev 호환성 |

dev에서 `lax`인 이유: `strict`도 localhost에서 동작하지만, 브라우저별 localhost 처리 차이와 개발 도구 호환성 문제를 피하기 위해 `lax` 사용. prod에서만 `strict` 적용.

### 5.2 CORS 설정

#### 환경별 설정

```typescript
await fastify.register(cors, {
  origin: [env.CLIENT_URL],
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-CSRF-Token'],
  maxAge: env.NODE_ENV === 'production' ? 7200 : 0,
});
```

| 설정 | 값 | 이유 |
|---|---|---|
| `origin` | `CLIENT_URL` 단일 | 허용된 프론트엔드만 |
| `credentials` | `true` | 세션 쿠키 포함 |
| `methods` | 명시적 나열 | 허용 메서드 제한 |
| `allowedHeaders` | 명시적 나열 | CSRF 토큰 헤더 포함 |
| `maxAge` | prod 7200, dev 0 | preflight 캐시 (prod: Chrome 최대값) |

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

CSRF 토큰 발급: 기존 `GET /api/auth/csrf-token` 엔드포인트 유지. 클라이언트가 페이지 로드 시 토큰을 받아 이후 요청에 `X-CSRF-Token` 헤더로 포함.

### 5.5 Swagger 프로덕션 비활성화

```typescript
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

### 보안 설정 요약

| 항목 | Development | Production |
|---|---|---|
| 쿠키 `secure` | false | true |
| 쿠키 `httpOnly` | true | true |
| 쿠키 `sameSite` | lax | strict |
| CORS origin | `CLIENT_URL` | `CLIENT_URL` |
| CORS maxAge | 0 | 7200 (Chrome 최대) |
| CSRF | 적용 | 적용 |
| HSTS | false | true |
| Swagger | 활성 | 비활성 |
| OAuth | 환경변수로 on/off | 비활성 (v1) |

### Helmet 설정

```typescript
contentSecurityPolicy: false,  // CSP는 Next.js가 담당 (클라이언트 이슈)
hsts: env.CLIENT_PROTOCOL === 'https',  // 기존 유지
// X-Frame-Options, X-Content-Type-Options 등 기본값 유지
```

### 에지 케이스

| 케이스 | 처리 |
|---|---|
| CSRF 토큰 만료 | 401 - 클라이언트에서 토큰 재발급 후 재시도 |
| OAuth 환경변수 부분 설정 (ID만, Secret 없음) | 서버 startup 시 Zod 검증 실패 - exit(1) |
| dev에서 CSRF 토큰 없이 테스트 | CSRF는 test 환경에서 비활성 (기존 동작 유지) |
| OAuth 활성화 시 `sameSite: strict` 충돌 | OAuth 콜백은 외부 리다이렉트이므로 `strict`에서 쿠키 누락. OAuth 활성화 시 `sameSite`를 `lax`로 변경 필요 |

## 수용 기준

- [ ] 프로덕션 쿠키에 `httpOnly`, `secure`, `sameSite: strict`가 설정된다
- [ ] dev 쿠키에 `httpOnly`, `sameSite: lax`가 설정된다
- [ ] CORS에 허용 methods, headers, maxAge가 명시된다
- [ ] Admin 라우트 전체에서 GET 제외 CSRF 검증이 동작한다
- [ ] 댓글/방명록 작성/삭제에서 CSRF 검증이 동작한다
- [ ] CSRF 토큰 없이 POST 요청 시 403이 반환된다
- [ ] 프로덕션에서 Swagger UI (`/docs`)에 접근할 수 없다
- [ ] OAuth 환경변수가 비어있으면 OAuth 라우트가 등록되지 않는다
- [ ] HSTS 헤더가 HTTPS 환경에서만 활성화된다
- [ ] Helmet CSP가 비활성화된다 (Next.js 담당)

## 의존성

- Blocked by: S-03, S-13
- Blocks: 없음

## 참고

- CSP는 서버(Fastify)가 아닌 클라이언트(Next.js)에서 설정한다. Fastify는 API 전용이므로 CSP 불필요.
- OAuth 활성화 시 `sameSite`를 `lax`로 변경해야 한다. v1에서는 OAuth 비활성이므로 `strict` 유지.
- test 환경에서 CSRF를 비활성화하여 테스트 편의성을 유지한다.
