# Auth system

> 관리자 로그인/로그아웃, CSRF 토큰 발급, OAuth 라우트 구조, 인증 훅 구현

## SPEC 참조

- `docs/server/api-spec.md` > 인증 방식, CSRF 보호, Rate limiting, Auth 섹션

## 상세

### 인증 방식

| 방식 | 설명 |
|---|---|
| **Admin Session** | `POST /api/auth/admin/login` 후 세션 쿠키 발급. `requireAdmin` 훅으로 보호 |
| **OAuth (Google/GitHub)** | Passport 기반. `request.user`로 접근. `requireAuth` 훅으로 보호 |
| **optionalAuth** | 인증 선택적. 비로그인 시에도 접근 가능 (게스트 댓글 등) |

### CSRF 보호

상태 변경 요청에 CSRF 토큰 필요. `GET /api/auth/csrf-token`으로 토큰 발급 후 요청 헤더에 포함.

적용 대상:
- `POST /api/auth/admin/logout`
- `POST /api/posts/:postId/comments`
- `DELETE /api/comments/:id`
- `POST /api/guestbook`
- `DELETE /api/guestbook/:id`
- `POST /api/stats/view`

### Rate limiting

| 엔드포인트 | 제한 |
|---|---|
| `POST /api/auth/admin/login` | 5 req/min |
| `POST /api/posts/:postId/comments` | 10 req/min |
| `POST /api/guestbook` | 10 req/min |
| `POST /api/stats/view` | 30 req/min |

### Auth 엔드포인트

| Method | Path | Auth | 설명 |
|---|---|---|---|
| GET | `/api/auth/google` | - | Google OAuth 리다이렉트 |
| GET | `/api/auth/google/callback` | - | Google OAuth 콜백 |
| GET | `/api/auth/github` | - | GitHub OAuth 리다이렉트 |
| GET | `/api/auth/github/callback` | - | GitHub OAuth 콜백 |
| GET | `/api/auth/csrf-token` | - | CSRF 토큰 발급 |
| POST | `/api/auth/admin/login` | - | 관리자 로그인 (5 req/min) |
| POST | `/api/auth/admin/logout` | CSRF | 관리자 로그아웃 (세션 파기) |
| GET | `/api/auth/me` | - | 현재 로그인 사용자 정보 |

#### GET `/api/auth/csrf-token`

**Response 200:**
```json
{ "token": "string" }
```

#### POST `/api/auth/admin/login`

**Request Body:**
```json
{ "username": "string", "password": "string" }
```

**Response 200:**
```json
{ "admin": { "id": 1, "username": "...", "createdAt": "ISO", "updatedAt": "ISO", "lastLoginAt": "ISO" } }
```

- Rate limit: 5 req/min
- 비밀번호는 argon2로 검증

#### POST `/api/auth/admin/logout`

**Response:** 204 No Content

- CSRF 토큰 필요
- 세션을 파기한다

#### GET `/api/auth/me`

**Response 200 (Admin):**
```json
{ "type": "admin", "id": 1, "username": "...", "createdAt": "ISO", "updatedAt": "ISO", "lastLoginAt": "ISO" }
```

**Response 200 (OAuth):**
```json
{ "type": "oauth", "id": 1, "name": "...", "email": "...", "githubId": "...", "googleEmail": "..." }
```

**Response 401:** 미인증

### 인증 훅

| 훅 | 용도 | 실패 시 |
|---|---|---|
| `requireAdmin` | Admin 세션 확인 | 401/403 |
| `requireAuth` | OAuth 사용자 확인 | 401 |
| `optionalAuth` | 인증 선택적. 비로그인 시 `request.user = null` | 통과 |

### OAuth 라우트 (구조만)

Google/GitHub OAuth 라우트는 Passport 기반으로 구현하되, v1에서는 환경변수가 비어있으면 해당 전략을 등록하지 않는다.

- `GET /api/auth/google` - Google OAuth 리다이렉트
- `GET /api/auth/google/callback` - Google OAuth 콜백
- `GET /api/auth/github` - GitHub OAuth 리다이렉트
- `GET /api/auth/github/callback` - GitHub OAuth 콜백

## 수용 기준

- [ ] `POST /api/auth/admin/login`이 username/password를 검증하고 세션 쿠키를 발급한다
- [ ] 비밀번호가 argon2로 검증된다
- [ ] 로그인 시 `lastLoginAt`이 업데이트된다
- [ ] `POST /api/auth/admin/login`에 5 req/min rate limit이 적용된다
- [ ] `POST /api/auth/admin/logout`이 세션을 파기하고 204를 반환한다
- [ ] 로그아웃 시 CSRF 토큰이 검증된다
- [ ] `GET /api/auth/csrf-token`이 CSRF 토큰을 반환한다
- [ ] `GET /api/auth/me`가 Admin 세션일 때 admin 정보를, OAuth 세션일 때 OAuth 정보를 반환한다
- [ ] `GET /api/auth/me`가 미인증 시 401을 반환한다
- [ ] `requireAdmin` 훅이 Admin 세션이 없으면 401/403을 반환한다
- [ ] `requireAuth` 훅이 OAuth 세션이 없으면 401을 반환한다
- [ ] `optionalAuth` 훅이 미인증 시에도 통과하고 `request.user = null`로 설정한다
- [ ] OAuth 라우트 구조가 존재하며 환경변수로 활성/비활성 전환 가능하다

## 의존성

- Blocked by: S-01, S-02
- Blocks: S-04~S-12, S-14

## 참고

- OAuth는 v1에서 서버 구현만 유지하고 클라이언트는 미지원한다. 환경변수(`GOOGLE_CLIENT_ID`, `GITHUB_CLIENT_ID`)가 비어있으면 해당 전략을 등록하지 않는다.
- CSRF 토큰은 `X-CSRF-Token` 헤더로 전달한다.
- Admin 세션 쿠키의 보안 플래그(httpOnly, secure, sameSite)는 S-14에서 설정한다.
