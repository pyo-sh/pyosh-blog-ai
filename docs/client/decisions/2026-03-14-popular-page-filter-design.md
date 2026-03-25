# Popular Page Filter Design

## Summary

`/popular` page keeps SSR rendering and adds a query-parameter-driven period filter.
Only `7` and `30` are valid `days` values.
Missing or invalid values redirect to `/popular?days=7`.

## Context

Issue `client#61` requires a public popular-posts page with:

- SSR rendering
- `days` query parameter support
- visible `7일 / 30일` period selection
- ranking, title link, `pageviews`, and `uniques`

The page already exists, but it currently hardcodes `30` days and has no URL-driven filtering.

## Options Considered

### 1. Minimal single-file update

Handle query parsing, redirect, data fetch, and tab UI inside `src/app/popular/page.tsx`.

- Pros: fastest
- Cons: mixes validation, navigation, and presentation in one file

### 2. Page-focused separation

Keep route concerns in `page.tsx`, and move period selector / list rendering into a small presentation component near the page.

- Pros: clearer responsibilities, easier future extension
- Cons: one extra file

### 3. Reusable feature-level filter

Promote the period selector into a reusable `features` or `widgets` module.

- Pros: reusable
- Cons: unnecessary abstraction for a single page

## Decision

Choose option 2.

`page.tsx` will:

- read `searchParams.days`
- validate against `7` and `30`
- redirect invalid or missing values to `/popular?days=7`
- fetch SSR data via `fetchPopularPosts(days)`

A page-local presentation component will:

- render the hero copy
- render `7일 / 30일` pill tabs as links
- show the ranked list with pageviews and uniques
- preserve the current visual style

## Data Flow

1. Request arrives at `/popular` with optional `days`
2. Server validates the query param
3. Invalid state redirects to canonical URL
4. Valid state fetches `fetchPopularPosts(days)`
5. Server renders the selected filter state and ranked results

## Error Handling

- Missing `days` redirects to `?days=7`
- Non-numeric or unsupported `days` redirects to `?days=7`
- Empty result set renders the existing empty-state section

## Testing

For client verification, run:

`cd client && pnpm compile:types && pnpm lint && pnpm build`
