# fix: PaginatedResponse meta.total 필드 수정

> **Status**: draft
> **Type**: fix
> **Priority**: priority:1
> **Phase**: 1
> **Labels**: fix, priority:1

## Goal

서버 응답 스키마와 일치하도록 클라이언트 PaginatedResponse의 `meta.totalCount`를 `meta.total`로 수정

## Context

서버 `PaginationMetaSchema`는 `total` 필드를 사용하지만, 클라이언트 `PaginatedResponse<T>` 인터페이스는 `totalCount`로 정의됨. Phase 1 시작 전 반드시 수정 필요.

- Plan reference: `docs/client/plans/phase-1-core.md` (Prerequisite 섹션)

## Requirements

- `src/shared/api/types.ts`의 `PaginatedResponse` 인터페이스에서 `totalCount` → `total`로 변경
- 관련 타입을 참조하는 모든 코드가 빌드 통과하는지 확인

## Scope

- Modify: `src/shared/api/types.ts`

## Definition of Done

- [ ] `meta.totalCount` → `meta.total` 변경
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
- [ ] 커밋 완료
