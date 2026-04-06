# Decisions Index — Server

> 아키텍처/기술 결정 기록. 상태: draft → accepted | rejected

<!-- 새 항목은 아래에 추가 -->

## 001 - Rename admin persistence from email to username

- **File**: `decisions/decision-001-admin-persistence-rename-email-to-username.md`
- **Date**: 2026-04-06
- **Status**: draft
- **Summary**: Replace legacy admin `email` identifier naming in persistence and service layers with `username`
- **Keywords**: admin, auth, username, migration, drizzle

## 002 - Change admin auth route contract to username

- **File**: `decisions/decision-002-admin-auth-route-username-contract.md`
- **Date**: 2026-04-06
- **Status**: draft
- **Summary**: Update admin login and current-user API contracts to use `username`
- **Keywords**: admin, auth, route, username, openapi

## 003 - Enforce CSRF on category and asset mutations

- **File**: `decisions/decision-003-csrf-enforcement-for-categories-and-assets.md`
- **Date**: 2026-04-06
- **Status**: draft
- **Summary**: Make category and asset mutation routes match documented CSRF requirements
- **Keywords**: csrf, categories, assets, security, routes
