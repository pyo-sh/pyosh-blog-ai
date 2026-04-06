# Decision 004: Fix admin guestbook method contract

## Metadata
- **Date**: 2026-04-06
- **Status**: draft
- **Type**: bug
- **Area**: client

## Symptom

관리자 방명록 `hide/restore`는 서버에서 `PATCH`인데, 클라이언트 helper는 `DELETE`로 호출한다.

## Cause

단건/벌크 patch helper가 delete helper를 재사용하면서 HTTP method가 잘못 고정되었다.

## Solution

단건/벌크 상태 변경 helper를 실제 서버 라우트와 동일한 `PATCH`로 분리하고, 삭제 계열 helper와 역할을 명확히 구분한다.

## Issue Draft
- **Type**: bug
- **Area**: client
- **Symptom**: 관리자 방명록 상태 변경이 잘못된 HTTP method를 사용한다.
- **Cause**: patch helper가 delete helper를 우회 재사용한다.
- **Solution**: patch 전용 helper를 별도로 만들고 manager 화면은 그 helper를 사용한다.
- **Dependencies**: 없음
- **Priority**: priority:1

## Template mapping

- `bug.yml`
- `area`: `client`
- `symptom`: guestbook hide/restore가 잘못된 HTTP method 사용
- `cause`: patch helper가 delete helper를 재사용
- `solution`: patch 전용 helper 분리
- `scope`: 아래 Scope 섹션 사용
- `dependencies`: `없음`
- `priority`: `priority:1`

## Scope

- Modify: `client/src/entities/guestbook/api.ts`
- Review: `client/src/features/guestbook-manager/ui/guestbook-manager.tsx`

## Acceptance criteria

- 단건 `hide/restore`는 `PATCH /api/admin/guestbook/:id?action=...`를 호출한다.
- 벌크 `hide/restore`는 `PATCH /api/admin/guestbook/bulk`를 호출한다.
- soft/hard delete helper와 patch helper의 의미가 분리된다.
- manager 화면 호출부가 helper 의미와 일치한다.

## Verify

- `(cd client && pnpm compile:types && pnpm lint && pnpm build)`
