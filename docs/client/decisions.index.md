# Decisions Index — Client

> 아키텍처/기술 결정 기록. 상태: draft → accepted | rejected

<!-- 새 항목은 아래에 추가 -->

## 001 - Docs branch git strategy

- **File**: `decisions/decision-001-docs-branch-strategy.md`
- **Date**: 2026-03-13
- **Status**: accepted
- **Summary**: All dev-log commits target long-lived `docs` branch; squash-merge to `main` via `/dev-archive`
- **Keywords**: dev-log, docs, git strategy, branching

## 002 - Align admin logout with CSRF contract

- **File**: `decisions/decision-002-admin-logout-csrf-alignment.md`
- **Date**: 2026-04-06
- **Status**: draft
- **Summary**: Change client admin logout to use CSRF-protected mutation flow
- **Keywords**: auth, logout, csrf, client

## 003 - Align client admin auth to username contract

- **File**: `decisions/decision-003-admin-login-username-contract.md`
- **Date**: 2026-04-06
- **Status**: draft
- **Summary**: Update client admin login and current-user models to use `username`
- **Keywords**: auth, admin, username, model, login

## 004 - Fix admin guestbook method contract

- **File**: `decisions/decision-004-admin-guestbook-method-alignment.md`
- **Date**: 2026-04-06
- **Status**: draft
- **Summary**: Make client admin guestbook hide/restore calls use the correct HTTP methods
- **Keywords**: guestbook, admin, patch, api, client

## 005 - Align post client models with actual API contract

- **File**: `decisions/decision-005-post-api-contract-alignment.md`
- **Date**: 2026-04-06
- **Status**: draft
- **Summary**: Separate or relax post response models and remove unsupported mutation fields
- **Keywords**: posts, api, types, contract, refactor

<!-- 새 항목은 아래에 추가 -->
