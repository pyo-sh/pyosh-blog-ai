# Decisions Index — Client

> 아키텍처/기술 결정 기록. 상태: draft → accepted | rejected

<!-- 새 항목은 아래에 추가 -->

## 001 - Docs branch git strategy

- **File**: `decisions/decision-001-docs-branch-strategy.md`
- **Date**: 2026-03-13
- **Status**: accepted
- **Summary**: All dev-log commits target long-lived `docs` branch; squash-merge to `main` via `/dev-archive`
- **Keywords**: dev-log, docs, git strategy, branching

## 002 - Public shell height and spacing

- **File**: `decisions/decision-002-public-shell-height-and-spacing.md`
- **Date**: 2026-04-10
- **Status**: accepted
- **Summary**: Rebuild the public shell as a vertical flex layout so the footer stays at the viewport bottom and the empty-looking header gap is removed
- **Keywords**: client, public-layout, footer, header, spacing, css

## 003 - Admin login screen simplification

- **File**: `decisions/decision-003-admin-login-screen-simplification.md`
- **Date**: 2026-04-10
- **Status**: accepted
- **Summary**: Simplify `/manage/login` to a centered login form on `bg-background-1` with decorative gradients removed
- **Keywords**: client, admin-login, layout, background, form, ux

## 004 - Admin routes must not render public header

- **File**: `decisions/decision-004-admin-routes-must-not-render-public-header.md`
- **Date**: 2026-04-10
- **Status**: accepted
- **Summary**: Exclude the public header from `/manage` routes so admin pages render only the admin chrome
- **Keywords**: client, admin, header, provider, routing, layout

## 005 - Category empty state must keep management controls

- **File**: `decisions/decision-005-category-empty-state-must-keep-controls.md`
- **Date**: 2026-04-10
- **Status**: accepted
- **Summary**: Keep the category page control box visible even when there are no categories so users can still create and manage categories
- **Keywords**: client, category, empty-state, control-box, management, ux

## 006 - Dev asset URL normalization and CSP split

- **File**: `decisions/decision-006-dev-asset-url-normalization-and-csp-split.md`
- **Date**: 2026-04-10
- **Status**: accepted
- **Summary**: Normalize relative asset URLs against the API origin in development and separate dev-only CSP allowances from the production policy
- **Keywords**: client, assets, uploads, csp, development, nextjs, middleware, fonts

<!-- 새 항목은 아래에 추가 -->
