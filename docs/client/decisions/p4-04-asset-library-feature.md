# feat: 에셋 라이브러리 feature + 페이지

> **Status**: draft
> **Type**: feat
> **Priority**: priority:3
> **Phase**: 4
> **Labels**: feat, priority:3
> **Depends on**: p4-03

## Goal

`/dashboard/assets` 에셋 라이브러리 페이지 (갤러리 + 업로드 + 삭제)

## Context

이미지 갤러리 그리드 + 드래그&드롭 업로드 영역 + URL 복사(plain/마크다운) + 삭제.

- Plan reference: `docs/client/plans/phase-4-extras.md` (Issue #18 → Task 2)

## Requirements

- AssetGrid: 이미지 그리드, hover 시 URL 복사/마크다운 복사/삭제 오버레이, 파일 크기/해상도 표시
- UploadZone: 드래그&드롭 + 클릭 업로드, 최대 5개/10MB, MIME 검증 (JPEG, PNG, GIF, WebP, SVG)
- Admin 에셋 페이지: TanStack Query + 페이지네이션

## Scope

- Create: `src/features/asset-uploader/ui/asset-grid.tsx`
- Create: `src/features/asset-uploader/ui/upload-zone.tsx`
- Create: `src/features/asset-uploader/index.ts`
- Create: `src/app/dashboard/assets/page.tsx`

## Definition of Done

- [ ] AssetGrid 갤러리 구현
- [ ] UploadZone 드래그&드롭 구현
- [ ] 에셋 관리 페이지 구현
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
