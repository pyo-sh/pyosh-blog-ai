# Decision 006: Dev Asset URL Normalization And CSP Split

## Metadata
- **Date**: 2026-04-10
- **Status**: accepted
- **Related Issue**: -

## Background
로컬 개발 환경에서 asset 업로드 이후 `client`가 `/uploads/...` 경로를 그대로 `<img src>`에 사용하면서 브라우저가 이를 Next.js 개발 서버 origin인 `http://localhost:3000/uploads/...`로 해석해 404가 발생했다.

동시에 `client` middleware가 주입하는 CSP report-only 정책 때문에 개발자 콘솔에 다음 로그가 누적되고 있다.

- Google Fonts stylesheet 로드 위반
- Next.js/React 개발 런타임의 `unsafe-eval` 관련 위반

첫 번째는 실제 기능 장애이고, 두 번째는 현재 `Report-Only` 기준에서는 동작을 막지 않지만 개발 환경 정책과 운영 정책이 섞여 있어 신호를 오염시키는 문제다.

## Option Comparison

### Option A: Client에서 상대 asset URL을 API origin 기준 절대 URL로 정규화하고, CSP는 dev/prod를 분리
- **Pros**: 현재 404를 가장 작은 변경으로 즉시 해결할 수 있다.
- **Pros**: 업로드 응답, 자산 목록, 썸네일, 에디터 삽입 등 모든 소비 지점에 같은 규칙을 적용할 수 있다.
- **Pros**: production CSP를 느슨하게 만들지 않고 dev에 필요한 허용만 한정적으로 추가할 수 있다.
- **Cons**: asset URL 정규화 책임이 클라이언트에 남는다.
- **Cost/Complexity**: low

### Option B: Server가 절대 asset URL을 반환하도록 API 계약을 변경
- **Pros**: 클라이언트는 별도 해석 없이 바로 렌더링할 수 있다.
- **Cons**: API 응답 계약 변경 범위가 커지고 base URL 책임이 서버로 이동한다.
- **Cost/Complexity**: medium

## AI Recommendation
> Option A를 권장한다. 현재 장애는 클라이언트가 상대 경로를 잘못된 origin으로 해석하는 문제이므로, 소비 지점에서 API origin 기준으로 정규화하는 편이 가장 안전하다.
>
> CSP도 development와 production을 같은 규칙으로 다루지 말고 분리해야 한다. dev에 필요한 예외를 production 정책에 섞지 않는 편이 맞다.

## Final Decision
> `client`는 `/uploads/...` 형태의 상대 asset URL을 렌더링하거나 복사 가능한 URL로 노출하기 전에 `NEXT_PUBLIC_API_URL` 기준 절대 URL로 정규화한다.
>
> 이 규칙은 업로드 직후 응답, 자산 목록 조회, 썸네일 선택, 게시글 에디터 내 이미지 삽입 등 asset URL을 소비하는 모든 클라이언트 경로에 공통 적용한다.
>
> CSP는 `client` middleware에서 dev/prod를 분리한다. development에서는 Google Fonts stylesheet 로드와 Next.js 개발 런타임에 필요한 예외만 한정적으로 허용하고, production에서는 더 엄격한 정책을 유지한다.

## Implementation Notes
- `client`에 asset URL 정규화 유틸을 추가한다.
- 정규화 규칙은 다음과 같다.
  - `http://`, `https://`, `blob:`, `data:`는 그대로 둔다.
  - `/uploads/...`처럼 루트 상대 경로는 `NEXT_PUBLIC_API_URL`을 prefix로 붙인다.
  - 그 외 상대 경로는 우선 보존하되 계약 위반 여부를 별도로 판단한다.
- asset API 응답 매핑 단계에서 URL 정규화를 수행해 UI 컴포넌트가 항상 렌더 가능한 값을 받도록 한다.
- development CSP는 다음 항목을 분리 검토한다.
  - `style-src`에 `https://fonts.googleapis.com`
  - `script-src`에 dev 한정 `'unsafe-eval'`

## Follow-up Actions
- [ ] asset 응답 매핑 계층에 URL 정규화 로직을 추가한다.
- [ ] 업로드 응답과 자산 목록 조회에 동일한 정규화가 적용되도록 정리한다.
- [ ] `middleware.ts`의 CSP를 dev/prod 분리 정책으로 수정한다.
- [ ] 관련 회귀 테스트 또는 최소 검증 경로를 추가한다.
