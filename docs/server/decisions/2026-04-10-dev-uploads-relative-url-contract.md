# Decision 002: Dev Uploads Relative URL Contract

## Metadata
- **Date**: 2026-04-10
- **Status**: accepted
- **Related Issue**: -

## Background
로컬 개발 환경에서 asset 업로드는 성공했고 파일도 `server`의 `uploads/` 디렉토리에 저장되었다. 하지만 `client`는 `/uploads/...` 경로를 자기 origin에서 해석해 404를 냈다.

이 문제의 직접 원인은 Fastify 정적 서빙 실패라기보다, asset API가 상대 경로를 반환하고 소비자가 이를 다른 origin으로 해석한 데 있다. 따라서 서버 쪽에서는 정적 서빙 계약을 명확히 유지하고, 실제 업로드 저장 위치와 `/uploads/*` 노출 경로가 일치하는지를 검증하는 것이 핵심이다.

## Option Comparison

### Option A: Server는 `/uploads/...` 상대 경로 계약을 유지하고, 정적 서빙 경로 검증에 집중
- **Pros**: 기존 API 응답 계약과 테스트를 크게 흔들지 않는다.
- **Pros**: `server` 책임을 파일 저장과 정적 파일 서빙으로 명확히 제한할 수 있다.
- **Cons**: 상대 경로 해석 책임이 소비자에게 남는다.
- **Cost/Complexity**: low

### Option B: Server가 절대 asset URL을 반환하도록 계약 변경
- **Pros**: 소비자 입장에서는 해석이 단순해진다.
- **Cons**: 환경별 base URL 규칙과 응답 계약 변경 부담이 서버로 이동한다.
- **Cons**: 기존 문서와 테스트를 함께 수정해야 한다.
- **Cost/Complexity**: medium

## AI Recommendation
> Option A를 권장한다. 이번 이슈에서 서버가 즉시 보장해야 할 것은 `uploads/` 저장 경로와 `/uploads/*` 정적 노출이 정확히 맞물리는지이며, API 계약 자체를 절대 URL로 넓히는 것은 별도 결정으로 다루는 편이 안전하다.

## Final Decision
> `server`는 dev 환경에서도 asset API의 URL 계약을 `/uploads/...` 상대 경로로 유지한다.
>
> 대신 Fastify의 `/uploads/*` 정적 서빙 경로가 실제 업로드 저장 디렉토리와 정확히 일치하는지 검증하고, dev 환경에서 저장 성공 후 즉시 접근 가능한 상태를 보장해야 한다.

## Implementation Notes
- `UPLOAD_DIR`와 Fastify static root의 관계를 명시적으로 점검한다.
- 업로드 저장 경로와 정적 서빙 경로가 어긋나는 경우 이를 빠르게 발견할 수 있는 검증 경로를 추가한다.
- 이번 결정 범위에서는 asset API를 절대 URL 반환 방식으로 바꾸지 않는다.

## Follow-up Actions
- [ ] `/uploads/*` 정적 서빙과 실제 업로드 저장 위치가 dev 환경에서 일치하는지 검증한다.
- [ ] 필요 시 정적 파일 접근 테스트 또는 최소 검증 경로를 추가한다.
- [ ] 상대 경로 계약을 전제한 API 문서와 구현이 일치하는지 재확인한다.
