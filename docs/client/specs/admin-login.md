# F-19: 관리자 로그인

**상태:** DRAFT
**최종 수정:** 2026-03-18

---

## 1. 개요

관리자 인증 시스템. 아이디/비밀번호 기반 로그인, 세션 관리, 관리 페이지 접근 제어를 제공한다.

## 2. 배경 및 동기

블로그 콘텐츠 관리를 위해 단일 관리자가 인증 후 관리 페이지에 접근한다. 관리자 계정은 개발자가 DB에 직접 등록하며, 보안상 계정 관리 UI는 제공하지 않는다.

## 3. 목표

- 관리자가 아이디/비밀번호로 로그인하여 관리 페이지에 접근한다
- 미인증 접근 시 로그인 페이지로 리다이렉트한다
- 로그아웃으로 세션을 즉시 파기할 수 있다

## 4. 비목표

- 관리자 계정 생성/수정 UI (DB 직접 관리)
- 비밀번호 변경 기능
- 비밀번호 찾기/재설정
- 멀티 관리자
- OAuth 로그인 (관리자에는 적용하지 않음. OAuth는 방명록/댓글 사용자 전용)

---

## 5. 상세 설계

### 5.1 사용자 흐름

#### 로그인

1. 방문자가 `/manage/*` 접근
2. 미인증 → `/manage/login`으로 리다이렉트 (`returnTo` 쿼리 파라미터 보존)
3. 아이디 + 비밀번호 입력 → 로그인 요청
4. 성공 → `returnTo` 경로 또는 `/manage`로 이동
5. 실패 → Toast로 에러 메시지 표시

#### 로그아웃

1. 사이드바 상단 로그아웃 버튼 클릭
2. 세션 파기 → `/manage/login`으로 이동

### 5.2 UI 구성

#### 로그인 페이지 (`/manage/login`)

```
┌─────────────────────────┐
│                         │
│   관리자 로그인          │
│                         │
│   [아이디          ]    │
│   [비밀번호        ]    │
│                         │
│   [로그인]              │
│                         │
└─────────────────────────┘
```

- 아이디 필드: `autoComplete="username"`
- 비밀번호 필드: `autoComplete="current-password"`
- 로그인 버튼: 요청 중 비활성화 + 로딩 상태 표시
- 에러 메시지: Toast (F-14) 사용

#### 사이드바 로그아웃

- 사이드바 상단에 로그아웃 버튼 배치
- 임시 구성 (추후 디자인 개선 가능)

### 5.3 데이터 흐름

```
로그인:
  Client POST /api/auth/admin/login { username, password }
    → Server: Argon2id 검증 → 세션 생성 (adminId 저장)
    → Client: 쿠키 자동 설정 → /manage 이동

인증 확인:
  Next.js Middleware → GET /api/auth/me (쿠키 전달)
    → 200: 접근 허용
    → 401: /manage/login 리다이렉트

로그아웃:
  Client POST /api/auth/admin/logout
    → Server: 세션 파기
    → Client: /manage/login 이동
```

### 5.4 컴포넌트 구조 (FSD)

| 계층 | 컴포넌트 | 역할 |
|---|---|---|
| `app` | `manage/login/page.tsx` | 로그인 페이지 |
| `app` | `manage/layout.tsx` | 관리 레이아웃 (사이드바 포함) |
| `app` | `middleware.ts` | `/manage/*` 경로 인증 가드 |
| `features` | `AdminLoginForm` | 로그인 폼 (아이디/비밀번호) |
| `entities` | `auth/api.ts` | `login()`, `logout()`, `fetchMe()` |
| `widgets` | `AdminSidebar` | 사이드바 (로그아웃 버튼 포함) |

## 6. API 연동

### POST /api/auth/admin/login

변경사항:

| 항목 | 현재 | 변경 |
|---|---|---|
| 요청 필드 | `{ email, password }` | `{ username, password }` |
| 비밀번호 검증 | 최소 8자 | 제한 없음 |

### POST /api/auth/admin/logout

변경 없음. CSRF 토큰 필수.

### GET /api/auth/me

변경 없음. 세션 기반 인증 확인.

### 서버 변경 필요사항

| 항목 | 설명 |
|---|---|
| DB 스키마 | `admins` 테이블 `email` → `username` (VARCHAR 100, UNIQUE) |
| 인증 로직 | `verifyCredentials(email, password)` → `verifyCredentials(username, password)` |
| 요청 스키마 | 로그인 body의 `email` → `username`, email 포맷 검증 제거 |
| 비밀번호 검증 | Zod 스키마에서 `min(8)` 제거 |

### 경로 변경 필요사항

| 항목 | 현재 | 변경 |
|---|---|---|
| Client 경로 | `/dashboard/*` | `/manage/*` |
| 로그인 페이지 | `/dashboard/login` | `/manage/login` |
| Middleware matcher | `/dashboard/:path*` | `/manage/:path*` |
| 사이드바 링크 | `/dashboard/...` | `/manage/...` |

## 7. 수용 기준

- [ ] `/manage/*` 미인증 접근 시 `/manage/login`으로 리다이렉트된다
- [ ] `returnTo` 파라미터로 원래 가려던 경로가 보존된다
- [ ] 아이디 + 비밀번호로 로그인할 수 있다
- [ ] 로그인 성공 시 `/manage`로 이동한다
- [ ] 로그인 실패 시 Toast로 에러 메시지가 표시된다
- [ ] 로그인 요청 중 폼이 비활성화되고 로딩 상태가 표시된다
- [ ] 세션 만료 시간은 24시간이다
- [ ] 사이드바 상단에 로그아웃 버튼이 있다
- [ ] 로그아웃 클릭 시 세션이 파기되고 `/manage/login`으로 이동한다
- [ ] 로그인 엔드포인트에 rate limit 적용 (5회/분)
- [ ] 접근성: 폼 필드에 적절한 label, autocomplete 속성 (A-01 참조)

## 8. 에지 케이스

| 케이스 | 처리 |
|---|---|
| 세션 만료 후 관리 페이지 접근 | `/manage/login`으로 리다이렉트, `returnTo` 보존 |
| 이미 로그인된 상태에서 `/manage/login` 접근 | `/manage`로 리다이렉트 |
| rate limit 초과 | 429 응답, Toast로 "잠시 후 다시 시도해 주세요" 표시 |
| 서버 연결 실패 | Toast로 네트워크 에러 메시지 표시 |
| 비밀번호 미입력 | 클라이언트 required 검증 |

## 9. 의존성

- F-14: Toast (에러 메시지 표시)
- 서버: `admins` 테이블 스키마 변경 (`email` → `username`)

## 10. 미해결 사항

없음. 모든 사항 확정됨.
