# feat: Asset entity types + API

> **Status**: draft
> **Type**: feat
> **Priority**: priority:3
> **Phase**: 4
> **Labels**: feat, priority:3

## Goal

에셋(이미지) 엔티티 타입과 API 함수 구현

## Context

에셋 목록 조회, 멀티파일 업로드 (FormData), 삭제 API. 업로드는 CSRF 토큰 + FormData로 직접 fetch.

- Plan reference: `docs/client/plans/phase-4-extras.md` (Issue #18 → Task 1)

## Requirements

- `Asset`: id, url, mimeType, sizeBytes, width, height, createdAt
- `fetchAssets(page)`: clientFetch (PaginatedResponse)
- `uploadAssets(files: File[])`: FormData + CSRF 토큰, POST /api/assets/upload
- `deleteAsset(id)`: clientMutate

## Scope

- Create: `src/entities/asset/model.ts`
- Create: `src/entities/asset/api.ts`
- Create: `src/entities/asset/index.ts`

## Definition of Done

- [ ] Asset 타입 + API 함수 구현
- [ ] multipart upload 동작
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
