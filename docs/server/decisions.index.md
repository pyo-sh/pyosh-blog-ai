# Decisions Index — Server

> 아키텍처/기술 결정 기록. 상태: draft → accepted | rejected

<!-- 새 항목은 아래에 추가 -->

| ID  | 제목 | 날짜 | 상태 | 태그 |
| --- | --- | --- | --- | --- |
| 001 | Admin 계정 로컬 TUI 관리 스크립트 설계 | 2026-04-10 | accepted | #admin #tui #operations #scripts |
| 002 | API Spec and Test Alignment Baseline | 2026-04-10 | accepted | #api-spec #testing #contracts #documentation |
| 003 | Dev uploads 상대 경로 계약 유지 및 정적 서빙 검증 | 2026-04-10 | accepted | #assets #uploads #static #development #api-contract |

## 상세 문서

- [2026-04-10-admin-tui-management-design.md](./decisions/2026-04-10-admin-tui-management-design.md) - env 기반 DB 연결로 admin 계정 조회/생성/수정/삭제를 수행하는 로컬 전용 TUI 스크립트 설계
- [2026-04-10-api-spec-test-alignment.md](./decisions/2026-04-10-api-spec-test-alignment.md) - API 스펙 기준 미검증 route와 stale 문서 서술을 정리하고 route-level contract test를 기준 단위로 확정
- [2026-04-10-dev-uploads-relative-url-contract.md](./decisions/2026-04-10-dev-uploads-relative-url-contract.md) - dev 환경에서 asset API는 `/uploads/...` 상대 경로 계약을 유지하고, Fastify 정적 서빙 경로와 실제 업로드 저장 위치 일치 여부를 검증한다
