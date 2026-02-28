---
name: brainstorming
description: "You MUST use this before any creative work - creating features, building components, adding functionality, or modifying behavior. Explores user intent, requirements and design before implementation."
---

# Brainstorming Ideas Into Designs

## Overview

Help turn ideas into fully formed designs and specs through natural collaborative dialogue.

Start by understanding the current project context, then ask questions one at a time to refine the idea. Once you understand what you're building, present the design and get user approval.

<HARD-GATE>
Do NOT invoke any implementation skill, write any code, scaffold any project, or take any implementation action until you have presented a design and the user has approved it. This applies to EVERY project regardless of perceived simplicity.
</HARD-GATE>

## Anti-Pattern: "This Is Too Simple To Need A Design"

Every project goes through this process. A todo list, a single-function utility, a config change — all of them. "Simple" projects are where unexamined assumptions cause the most wasted work. The design can be short (a few sentences for truly simple projects), but you MUST present it and get approval.

## Checklist

You MUST create a task for each of these items and complete them in order:

1. **Determine target area** — identify which area (client / server / workspace) this work targets
2. **Explore project context** — check `{area}/CLAUDE.md`, `docs/{area}/` records, recent commits
3. **Ask clarifying questions** — one at a time, understand purpose/constraints/success criteria
4. **Propose 2-3 approaches** — with trade-offs and your recommendation
5. **Present design** — in sections scaled to their complexity, get user approval after each section
6. **Write design doc** — save to `docs/workspace/decisions/YYYY-MM-DD-<topic>-design.md` and commit
7. **Transition to implementation** — invoke `/writing-plans` skill to create implementation plan

## Area Selection

| Area | When to use |
|------|-------------|
| `client` | Next.js frontend (FSD architecture, TailwindCSS, React) |
| `server` | Fastify API (Drizzle ORM, MySQL, Zod, Vitest) |
| `workspace` | Root repo (tools/, docs/, skills/, CLAUDE.md, Docker/tmux) |

Read `{area}/CLAUDE.md` for tech stack and coding patterns. Read `docs/{area}/` for past decisions, findings, and progress.

## Process Flow

```dot
digraph brainstorming {
    "Determine target area" [shape=box];
    "Explore project context" [shape=box];
    "Ask clarifying questions" [shape=box];
    "Propose 2-3 approaches" [shape=box];
    "Present design sections" [shape=box];
    "User approves design?" [shape=diamond];
    "Write design doc" [shape=box];
    "Invoke writing-plans" [shape=doublecircle];

    "Determine target area" -> "Explore project context";
    "Explore project context" -> "Ask clarifying questions";
    "Ask clarifying questions" -> "Propose 2-3 approaches";
    "Propose 2-3 approaches" -> "Present design sections";
    "Present design sections" -> "User approves design?";
    "User approves design?" -> "Present design sections" [label="no, revise"];
    "User approves design?" -> "Write design doc" [label="yes"];
    "Write design doc" -> "Invoke writing-plans";
}
```

**The terminal state is invoking `/writing-plans`.** Do NOT invoke `/frontend-design`, `/dev-build`, or any other implementation skill. The ONLY skill you invoke after brainstorming is `/writing-plans`.

## The Process

**Determining target area:**
- Identify which area the idea targets (client / server / workspace)
- If it spans multiple areas, note all affected areas — the primary area drives context exploration

**Understanding the idea:**
- Read `{area}/CLAUDE.md` for tech stack, directory structure, coding patterns
- Read `docs/{area}/decisions.index.md` and `docs/{area}/findings.index.md` for past context
- Check recent commits in the target area: `cd {area} && git log --oneline -10`
- Ask questions one at a time to refine the idea
- Prefer multiple choice questions when possible, but open-ended is fine too
- Only one question per message — if a topic needs more exploration, break it into multiple questions
- Focus on understanding: purpose, constraints, success criteria

**Exploring approaches:**
- Propose 2-3 different approaches with trade-offs
- Present options conversationally with your recommendation and reasoning
- Lead with your recommended option and explain why

**Presenting the design:**
- Once you believe you understand what you're building, present the design
- Scale each section to its complexity: a few sentences if straightforward, up to 200-300 words if nuanced
- Ask after each section whether it looks right so far
- Cover: architecture, components, data flow, error handling, testing
- Be ready to go back and clarify if something doesn't make sense

## After the Design

**Documentation:**
- Write the validated design to `docs/workspace/decisions/YYYY-MM-DD-<topic>-design.md`
- Commit: `docs: design - <topic>`

**Implementation:**
- Invoke the `/writing-plans` skill to create a detailed implementation plan
- Do NOT invoke any other skill. `/writing-plans` is the next step.

## Key Principles

- **One question at a time** — Don't overwhelm with multiple questions
- **Multiple choice preferred** — Easier to answer than open-ended when possible
- **YAGNI ruthlessly** — Remove unnecessary features from all designs
- **Explore alternatives** — Always propose 2-3 approaches before settling
- **Incremental validation** — Present design, get approval before moving on
- **Be flexible** — Go back and clarify when something doesn't make sense
- **Area-aware** — Always check the target area's CLAUDE.md and existing docs first
