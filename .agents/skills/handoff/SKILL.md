---
name: handoff
description: Create or update a handoff document for the next agent to continue work with fresh context. Use when: (1) switching to a new conversation, (2) context window is getting large, (3) user says "handoff", "save context", "wrap up for next session", or similar.
---

Save to `{root}/.workspace/handoffs/handoff_{summary}.md` where `{summary}` is a one-word topic.

**Find root**: Walk up from CWD to find the directory containing `.agents/` (do NOT use `git rev-parse` — this monorepo has multiple independent git repos).

If the file already exists, read it first to preserve prior context.

## Template

```markdown
# Handoff: {summary}

## Goal

What we're trying to accomplish

## Current Progress

What's been done so far

## What Worked

Approaches that succeeded

## What Didn't Work

Approaches that failed (so they're not repeated)

## Next Steps

Clear action items for continuing
```

Tell the user the full file path so they can provide it to a fresh conversation.
