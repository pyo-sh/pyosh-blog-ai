# Decisions Index — Client

> 아키텍처/기술 결정 기록. 상태: draft → accepted | rejected

<!-- 새 항목은 아래에 추가 -->

## 001 - Docs branch git strategy

- **File**: `decisions/decision-001-docs-branch-strategy.md`
- **Date**: 2026-03-13
- **Status**: accepted
- **Summary**: All dev-log commits target long-lived `docs` branch; squash-merge to `main` via `/dev-archive`
- **Keywords**: dev-log, docs, git strategy, branching

<!-- 새 항목은 아래에 추가 -->

## 003 - SPEC 기반 Client Issue 생성 전략

- **File**: `decisions/decision-003-spec-to-issue-strategy.md`
- **Date**: 2026-03-26
- **Status**: draft
- **Summary**: 35개 client spec 파일을 1:1로 Issue에 매핑하고, 공유 deployment spec의 client 부분 3개를 추가하여 총 38개 Client Issue를 생성한다.
- **Keywords**: spec, issue, feature-index, reimplementation, 1:1 mapping

## 002 - Category admin feature structure

- **File**: `decisions/2026-03-14-category-admin-design.md`
- **Date**: 2026-03-14
- **Status**: accepted
- **Summary**: Keep `/dashboard/categories` as a thin app entry and place query/mutation/modal orchestration in `features/category-manager`
- **Keywords**: client, admin, categories, FSD, TanStack Query
