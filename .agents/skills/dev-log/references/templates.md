# File Templates

## findings.index.md

```markdown
# Findings Index

## 001 - Next.js App Router Selection Rationale
- **File**: `findings/findings.001-nextjs-app-router.md`
- **Date**: 2026-02-01
- **Summary**: Chose App Router over Pages Router. RSC, Streaming, Layouts advantages.
- **Keywords**: Next.js, App Router, RSC

## 002 - TailwindCSS v4 Token Naming
- **File**: `findings/findings.002-tailwind-v4-tokens.md`
- **Date**: 2026-02-05
- **Summary**: kebab-case token naming rules and @theme block usage.
- **Keywords**: TailwindCSS, v4, tokens
```

## findings/findings.NNN-topic.md

```markdown
# [Topic]

## Metadata
- **Date**: YYYY-MM-DD
- **Related Issue**: #N

## Problem
The problem or situation requiring a choice

## Research

### Option A
- Pros: ...
- Cons: ...

### Option B
- Pros: ...
- Cons: ...

## Decision
Final choice and reasoning

## Implementation Guide
(Optional) Notes for actual implementation

## References
- [Link 1](URL)
```

## progress.index.md

```markdown
# Progress Index

## 2026-02-15
- **File**: `progress/progress.2026-02-15.md`
- **Summary**: Post card component complete. TailwindCSS tokens applied.
- **Tags**: #component #ui #tailwind

## 2026-02-10
- **File**: `progress/progress.2026-02-10.md`
- **Summary**: Drizzle ORM schema — 13 tables designed.
- **Tags**: #database #schema #drizzle
```

## progress/progress.YYYY-MM-DD.md

```markdown
# Progress: YYYY-MM-DD

## Completed
- [x] Task 1: Details (#IssueNumber)
- [x] Task 2: Details

## Discoveries
- Technical insights or unexpected issues

## Issues & Resolutions
- **Issue**: Problem description
- **Resolution**: How it was solved

## Next Steps
- [ ] Immediate next task
- [ ] Future task

## Notes
- Related findings: `findings/findings.NNN-topic.md`
```

## decisions.index.md

```markdown
# Decisions Index

## 001 - Auth Strategy Selection
- **File**: `decisions/decision-001-auth-strategy.md`
- **Date**: 2026-02-20
- **Status**: accepted
- **Summary**: Chose OAuth2 + Session-based auth
- **Keywords**: auth, OAuth, session
```

## decisions/decision-NNN-topic.md

```markdown
# Decision NNN: [Title]

## Metadata
- **Date**: YYYY-MM-DD
- **Status**: draft | accepted | rejected
- **Related Issue**: #N

## Background
Why this decision is needed

## Option Comparison

### Option A: [Name]
- **Pros**: ...
- **Cons**: ...
- **Cost/Complexity**: low/medium/high

### Option B: [Name]
- **Pros**: ...
- **Cons**: ...
- **Cost/Complexity**: low/medium/high

## AI Recommendation
> AI-analyzed recommended option with rationale

## Final Decision
> User-confirmed final decision (leave blank in draft)

## Follow-up Actions
- [ ] Implementation item 1
- [ ] Implementation item 2
```
