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

## 002 - Category admin feature structure

- **File**: `decisions/2026-03-14-category-admin-design.md`
- **Date**: 2026-03-14
- **Status**: accepted
- **Summary**: Keep `/dashboard/categories` as a thin app entry and place query/mutation/modal orchestration in `features/category-manager`
- **Keywords**: client, admin, categories, FSD, TanStack Query
