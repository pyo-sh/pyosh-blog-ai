# [F-34c] CSP (Content Security Policy)

> Next.js middleware에서 nonce 기반 CSP 헤더를 설정하여 XSS 공격을 방어한다. 단계적으로 report-only에서 실제 차단으로 전환한다.

## SPEC 참조

- `docs/specs/deploy-security.md` (섹션 5.4 CSP)

## 상세 설계

### Nonce 기반 CSP

Next.js App Router는 하이드레이션을 위해 HTML에 인라인 `<script>`를 삽입한다. `script-src 'self'`만 설정하면 이 인라인 스크립트가 차단되어 페이지가 동작하지 않는다.

이를 해결하기 위해 **nonce**(Number used Once)를 사용한다. 매 요청마다 랜덤 토큰을 생성하여 CSP 헤더와 인라인 스크립트에 동일한 nonce를 부여하면, nonce가 일치하는 스크립트만 실행이 허용된다. 공격자가 삽입한 스크립트에는 nonce가 없으므로 차단된다.

```
요청 흐름:
1. 브라우저가 페이지 요청
2. middleware가 랜덤 nonce 생성 (예: "abc123xyz")
3. CSP 헤더: script-src 'self' 'nonce-abc123xyz'
4. Next.js 인라인 스크립트: <script nonce="abc123xyz">...</script>
5. 브라우저: nonce 일치 → 실행 허용, nonce 없음 → 차단
```

### Next.js middleware에서 nonce 생성

```typescript
// middleware.ts
import { NextResponse } from 'next/server';

export function middleware(request: NextRequest) {
  const nonce = Buffer.from(crypto.randomUUID()).toString('base64');
  const isDev = process.env.NODE_ENV === 'development';
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || '';

  const cspDirectives = [
    "default-src 'self'",
    isDev
      ? "img-src 'self' http: https: data: blob:"
      : "img-src 'self' https: data: blob:",
    `script-src 'self' 'nonce-${nonce}'`,
    "style-src 'self' 'unsafe-inline'",
    "font-src 'self' https://fonts.gstatic.com",
    `connect-src 'self' ${apiUrl}`,
  ].join('; ');

  const response = NextResponse.next();

  // 1단계: report-only
  response.headers.set('Content-Security-Policy-Report-Only', cspDirectives);

  // nonce를 헤더로 전달 (layout.tsx에서 읽어 사용)
  response.headers.set('x-nonce', nonce);

  return response;
}
```

### layout.tsx에서 nonce 적용

```typescript
// app/layout.tsx
import { headers } from 'next/headers';

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const nonce = (await headers()).get('x-nonce') || '';

  return (
    <html>
      <body>
        {/* Next.js가 nonce prop을 받으면 인라인 스크립트에 자동 적용 */}
        <Script strategy="beforeInteractive" nonce={nonce} />
        {children}
      </body>
    </html>
  );
}
```

### Report-only 단계적 적용

초기 배포 시 `Content-Security-Policy-Report-Only` 헤더를 사용하여 차단 없이 위반 로그만 수집한다. 안정화 확인 후 실제 `Content-Security-Policy`로 전환한다.

| 단계 | 헤더 | 동작 |
|---|---|---|
| 1단계 | `Content-Security-Policy-Report-Only` | 차단 없음, 브라우저 콘솔에 위반 로그만 출력 |
| 2단계 | `Content-Security-Policy` | 실제 차단 (nonce 필수) |

- 1단계에서 nonce를 미리 적용해두면 2단계 전환 시 헤더 키만 변경하면 됨
- report-only에서 `[Report Only]` 위반 로그를 확인하여 디렉티브 조정
- 위반이 없음을 확인한 후 실제 차단으로 전환

### CSP 디렉티브 설명

| 디렉티브 | 값 | 이유 |
|---|---|---|
| `default-src` | `'self'` | 기본 동일 출처만 |
| `img-src` | `'self' https: data: blob:` | Admin URL 입력, 마크다운 외부 이미지, 썸네일 blob 미리보기 |
| `script-src` | `'self' 'nonce-{random}'` | nonce 일치 스크립트만 허용 (Next.js 인라인 스크립트 + XSS 방어) |
| `style-src` | `'self' 'unsafe-inline'` | Tailwind 인라인 스타일 허용 |
| `font-src` | `'self' fonts.gstatic.com` | Gothic A1 웹폰트 |
| `connect-src` | `'self' {API_URL}` | API 서버 연결 허용 |

dev에서 `img-src`에 `http:` 추가: Fastify 로컬 서버가 HTTP로 이미지 서빙.

## API 연동

없음. 클라이언트 보안 설정만 해당.

### 클라이언트 변경 필요사항

| 항목 | 설명 |
|---|---|
| `middleware.ts` | nonce 생성 + CSP 헤더 설정 (dev/prod 분리) |
| `app/layout.tsx` | nonce를 헤더에서 읽어 Script 컴포넌트에 전달 |

## 수용 기준

- [ ] Next.js에서 CSP 헤더가 응답에 포함된다
- [ ] CSP `script-src`에 요청별 nonce가 포함된다
- [ ] Next.js 인라인 스크립트에 nonce가 적용되어 정상 동작한다
- [ ] 초기 배포 시 `Content-Security-Policy-Report-Only`로 위반 로그만 수집한다
- [ ] 안정화 후 `Content-Security-Policy`로 전환하여 실제 차단한다
- [ ] 프로덕션에서 외부 HTTPS 이미지가 정상 로드된다
- [ ] dev에서 HTTP 이미지(Fastify 로컬 서버)가 정상 로드된다

## 에지 케이스

| 케이스 | 처리 |
|---|---|
| CSP가 정상 리소스를 차단 | 브라우저 콘솔에서 차단 로그 확인 후 디렉티브 조정 |
| 외부 HTTP 이미지 (prod) | CSP에 의해 차단 → Admin에게 HTTPS URL 사용 안내 |

## 의존성

- Blocked by: 없음
- Blocks: 없음
