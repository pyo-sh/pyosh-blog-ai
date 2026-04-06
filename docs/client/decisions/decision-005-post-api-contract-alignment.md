# Decision 005: Align post client models with actual API contract

## Metadata
- **Date**: 2026-04-06
- **Status**: draft
- **Type**: refactor
- **Area**: client

## Problem

Client post 모델은 목록 응답과 상세 응답을 같은 `Post` 타입으로 다루고 있고, 서버가 받지 않는 `contentModifiedAt` 수정까지 보내고 있다. 이 상태는 타입 안정성과 API 신뢰도를 동시에 떨어뜨린다.

## Improvement

- 목록/상세 응답 타입을 실제 API shape에 맞게 분리하거나 최소한 optionality를 조정한다.
- 서버가 지원하지 않는 `contentModifiedAt` mutation은 제거하거나 별도 결정 전까지 보내지 않도록 정리한다.

## Issue Draft
- **Type**: refactor
- **Area**: client
- **Problem**: Post 타입과 mutation payload가 실제 서버 계약과 어긋난다.
- **Improvement**: 목록/상세 타입을 재정의하고 unsupported mutation field를 제거한다.
- **Dependencies**: 없음
- **Priority**: priority:2

## Template mapping

- `refactor.yml`
- `area`: `client`
- `problem`: post list/detail/mutation contract mismatch
- `improvement`: 타입 분리 또는 optionality 조정, unsupported field 제거
- `scope`: 아래 Scope 섹션 사용
- `dependencies`: `없음`
- `priority`: `priority:2`

## Scope

- Modify: `client/src/entities/post/model.ts`
- Modify: `client/src/entities/post/api.ts`
- Modify: `client/src/widgets/admin-post-preview/ui/post-preview.tsx`
- Review: `client/src/app/manage/posts/page.tsx`
- Review: `client/src/features/post-list/ui/*`

## Acceptance criteria

- 목록 응답 타입이 상세 전용 필드를 강제하지 않는다.
- `updatePost`가 서버 schema에 없는 `contentModifiedAt`를 보내지 않는다.
- 관련 UI가 타입 오류 없이 빌드된다.
- list/detail 모델 차이가 코드에서 드러난다.

## Verify

- `(cd client && pnpm compile:types && pnpm lint && pnpm build)`
