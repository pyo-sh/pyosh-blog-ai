---
paths:
  - "src/**/*.{ts,tsx}"
---

# Frontend architecture and coding rules

- Keep the FSD import direction: `app -> widgets -> features -> entities -> shared`.
- `src/app/` is routing only. Do not move business logic there.
- Prefer PascalCase component names with named exports.
- Use `"use client"` only for components that require client-side interactivity.
- For class merging, use `cn` from `@/shared/lib/utils`.
