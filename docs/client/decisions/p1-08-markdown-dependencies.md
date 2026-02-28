# feat: 마크다운 렌더링 의존성 설치

> **Status**: draft
> **Type**: feat
> **Priority**: priority:1
> **Phase**: 1
> **Labels**: feat, priority:1

## Goal

마크다운 → HTML 변환 파이프라인에 필요한 패키지 설치

## Context

글 상세 페이지에서 contentMd를 HTML로 렌더링하기 위한 unified 생태계 패키지 + shiki 코드 하이라이팅.

- Plan reference: `docs/client/plans/phase-1-core.md` (Issue #5 → Task 1)

## Requirements

설치할 패키지:
- unified, remark-parse, remark-rehype
- rehype-stringify, rehype-sanitize
- shiki, @shikijs/rehype

## Scope

- Modify: `package.json`, `pnpm-lock.yaml`

## Tech Stack

unified + remark + rehype + shiki

## Definition of Done

- [ ] `pnpm add unified remark-parse remark-rehype rehype-stringify rehype-sanitize shiki @shikijs/rehype` 실행
- [ ] `pnpm compile:types && pnpm lint && pnpm build` 통과
