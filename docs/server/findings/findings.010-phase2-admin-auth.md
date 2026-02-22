# Findings 010: Phase 2 - Admin Auth Module

**날짜**: 2026-02-10
**태그**: #admin-auth #argon2 #session #fastify-passport

## 📝 요약

Admin 이메일/비밀번호 인증 시스템 구현. Argon2id 해싱, 세션 기반 인증, OAuth와 통합된 /me 엔드포인트 완성.

## 🎯 목표

1. Admin 계정 이메일/비밀번호 로그인
2. OAuth (Google/GitHub)와 Admin 인증 통합
3. 관리자 전용 라우트 보호를 위한 requireAdmin 훅

## 🔧 기술 선택

### Argon2id 선택 이유

**채택**: argon2 (Argon2id 알고리즘)

**비교 대상**:
- bcrypt: 가장 널리 사용되지만 GPU 공격에 취약
- scrypt: 메모리 하드 함수지만 병렬화 가능
- Argon2id: 메모리 하드 + 타이밍 공격 방어 + 2015 PHC 우승

**선택 근거**:
1. **최신 표준**: 2015 Password Hashing Competition 우승
2. **하이브리드 보안**: Argon2i (타이밍 공격 방어) + Argon2d (GPU 공격 방어)
3. **조절 가능한 파라미터**: memoryCost, timeCost로 미래 대응 가능
4. **OWASP 권장**: 신규 프로젝트에 Argon2id 권장

**설정값**:
```typescript
{
  type: argon2id,
  memoryCost: 65536,  // 64MB
  timeCost: 3,         // 3 iterations
}
```

**참고**:
- OWASP: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
- Argon2 RFC: https://datatracker.ietf.org/doc/html/rfc9106

### 세션 vs JWT

**채택**: @fastify/session (세션 기반 인증)

**비교**:
| 항목 | 세션 | JWT |
|------|------|-----|
| 저장소 | 서버 (DB/Redis) | 클라이언트 (쿠키/localStorage) |
| 무효화 | 즉시 가능 | 불가 (만료 대기) |
| 확장성 | 중앙화 필요 | 스테이트리스 |
| 보안 | 서버 제어 가능 | 탈취 시 무효화 불가 |

**선택 근거**:
1. **Admin 전용**: 관리자는 소수이므로 세션 부담 적음
2. **즉시 무효화**: 로그아웃/계정 삭제 시 즉시 세션 파기 필요
3. **기존 OAuth 통합**: @fastify/passport와 세션 공유

**트레이드오프**:
- 확장성: Redis 세션 스토어로 수평 확장 가능
- 현재: 단일 서버 + Drizzle 세션 스토어

## 🏗️ 구현 패턴

### Factory 함수 패턴

**기존 문제**: auth.route.ts가 FastifyPluginAsync 형태로 AdminService 주입 불가

**해결**:
```typescript
// Factory 함수로 변경
export function createAuthRoute(adminService: AdminService): FastifyPluginAsync {
  const authRoute: FastifyPluginAsync = async (fastify) => {
    // adminService 사용 가능
  };
  return authRoute;
}

// app.ts에서 사용
await fastify.register(createAuthRoute(adminService), { prefix: "/api/auth" });
```

**패턴 확산**:
- user.route.ts도 동일한 패턴 사용
- 향후 모든 라우트에서 일관된 DI 패턴

### requireAdmin Hook Factory

**문제**: 훅에서 AdminService 접근 필요

**해결**:
```typescript
// Factory 함수로 만들어 AdminService 주입
export function requireAdmin(adminService: AdminService) {
  return async (request: FastifyRequest) => {
    const adminId = request.session.get("adminId");
    if (!adminId) throw HttpError.forbidden("관리자 권한이 필요합니다");

    const admin = await adminService.getAdminById(adminId);
    request.admin = admin;
  };
}

// 사용 예시
fastify.get("/admin/posts", {
  preHandler: requireAdmin(adminService),
}, handler);
```

**장점**:
- 훅 내에서 DB 접근 가능
- 클로저로 adminService 캡처
- 타입 안전성 유지

### Admin/OAuth 통합 /me 엔드포인트

**설계**:
```typescript
GET /api/auth/me
Response:
  | { type: "admin", id, email, ... }
  | { type: "oauth", id, name, provider, ... }
```

**구현 로직**:
1. 세션에서 adminId 확인 → Admin 반환
2. 없으면 request.user (Passport) 확인 → OAuth 반환
3. 둘 다 없으면 → 401

**장점**:
- 클라이언트에서 단일 엔드포인트로 현재 사용자 확인
- type 필드로 Admin/OAuth 구분 가능

## 📊 테스트 결과

### 엔드포인트 검증

| 엔드포인트 | 테스트 케이스 | 결과 |
|-----------|--------------|------|
| POST /admin/setup | 초기 관리자 생성 | ✅ 201 |
| POST /admin/setup | 중복 시도 | ✅ 409 |
| POST /admin/login | 정상 로그인 | ✅ 200 + 세션 |
| POST /admin/login | 잘못된 비밀번호 | ✅ 401 |
| GET /me | Admin 로그인 후 | ✅ type: "admin" |
| GET /me | 로그아웃 후 | ✅ 401 |
| POST /admin/logout | 로그아웃 | ✅ 204 |

### 빌드 검증

```bash
pnpm compile:types  # ✅ 통과
pnpm lint           # ✅ 4 warnings (무시 가능)
pnpm build          # ✅ 통과
```

## 🐛 이슈 & 해결

### Issue 1: reflect-metadata 에러

**문제**:
```
Error: Cannot find module 'reflect-metadata'
```

**원인**: server.ts에서 불필요한 reflect-metadata import

**해결**: 주석 처리
```typescript
// import "reflect-metadata"; // Not needed for current stack
```

**근거**:
- reflect-metadata는 TypeORM, NestJS 등의 DI에서 사용
- 현재 스택은 순수 TypeScript + Drizzle (DI 없음)

### Issue 2: ESLint import/order

**문제**: import 순서 경고 (15개)

**해결**: `pnpm lint --fix`로 자동 수정

**결과**: 4개 경고만 남음 (무시 가능)

## 🎓 교훈

### 1. 비밀번호 해싱은 항상 최신 표준 사용

- bcrypt → Argon2id 마이그레이션 권장
- 조절 가능한 파라미터로 미래 대응

### 2. 세션 vs JWT는 사용 사례에 따라 결정

- **Admin**: 세션 (즉시 무효화 필요)
- **Public API**: JWT (스테이트리스)

### 3. Factory 함수 패턴으로 일관된 DI

- Fastify 플러그인과 DI를 결합하는 깔끔한 방법
- 타입 안전성 유지

### 4. /me 엔드포인트는 통합하는 것이 좋음

- Admin/OAuth를 단일 엔드포인트에서 처리
- type 필드로 구분 → 클라이언트 로직 단순화

## 📚 참고 자료

- [Argon2 RFC 9106](https://datatracker.ietf.org/doc/html/rfc9106)
- [OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [Fastify Passport](https://github.com/fastify/fastify-passport)
- [Fastify Session](https://github.com/fastify/session)

## 🔗 관련 파일

- [src/shared/password.ts](../../../server/src/shared/password.ts)
- [src/services/admin.service.ts](../../../server/src/services/admin.service.ts)
- [src/routes/auth/auth.route.ts](../../../server/src/routes/auth/auth.route.ts)
- [src/hooks/auth.hook.ts](../../../server/src/hooks/auth.hook.ts)
- [src/types/fastify.d.ts](../../../server/src/types/fastify.d.ts)
