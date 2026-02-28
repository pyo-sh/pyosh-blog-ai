# Priority Guide

## Label System

`priority:0` through `priority:7` (lower number = higher priority)

| Label | Meaning | Criteria |
|-------|---------|----------|
| `priority:0` | Critical — immediate | Service outage, security issues |
| `priority:1` | Urgent — ASAP | Blockers, core feature broken |
| `priority:2` | High — important | Required for next milestone |
| `priority:3` | Medium-High | Important but not immediate |
| `priority:4` | Medium | General features/improvements |
| `priority:5` | Medium-Low | Nice-to-have features |
| `priority:6` | Low — no rush | Long-term tasks |
| `priority:7` | Backlog — later | Future considerations |

## Judgment Criteria

1. **Phase**: Lower phase tends toward higher priority (not absolute)
2. **Dependencies**: Items others depend on get priority boost
3. **Comparison with existing Issues**: Rank equal or higher than similar existing Issues
4. **Impact scope**: Foundational work affecting multiple features gets priority boost
5. **Implementation vs documentation**: Same topic → implementation takes priority over docs

## Type Label Mapping

Assign type labels based on decision content:

| Content | Label |
|---------|-------|
| New feature | `✨FEAT` |
| Bug fix | `🐛BUG` |
| Documentation | `📚DOCS` |
| Refactoring | `♻️CLEANING` |
| Testing | `✅TEST` |
