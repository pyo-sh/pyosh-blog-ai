---
name: blog-polish
description: >-
  Lightly polish Korean personal essay drafts for readability, flow, paragraph
  rhythm, and natural wording without changing meaning. Use this when the user
  asks to revise, rewrite, polish, smooth, clean up, improve readability, or
  adjust style for a blog post while preserving the user's content, claims,
  emotion, conclusion, and first-person point of view. Also use this skill when
  the user asks to read or polish a bare blog filename, resolving it under
  .workspace/posts/ by default.
---

# Blog Polish

## Role

Polish an already-written personal blog essay. Improve readability and sentence
flow while preserving the user's content, argument, emotional temperature, and
point of view.

This skill is for refinement, not development. Do not add new ideas or make the
piece more persuasive by changing what it says.

## Non-Negotiables

- Do not add new facts, examples, arguments, interpretations, or conclusions.
- Do not remove the user's uncertainty, hesitation, anger, affection, or
  discomfort just to make the writing neat.
- Do not soften or intensify the emotional tone unless the user explicitly asks.
- Do not change the author's stance, target of criticism, or final takeaway.
- Do not convert the piece into a tutorial, explainer, marketing copy, or formal
  column.
- If a sentence can be read in two meaningfully different ways, ask before
  rewriting that part.

## Post Workspace

Use `.workspace/posts/` as the default workspace for blog post files.

- Resolve the repository root by walking up from the current directory until
  `.workspace/` or `.agents/` is found.
- When the user gives a bare filename such as `explain.md`, read
  `<root>/.workspace/posts/explain.md`.
- When the user gives a relative filename without an obvious project directory,
  prefer `<root>/.workspace/posts/<relative-path>`.
- When the user gives an absolute path, `.workspace/posts/...`, `docs/...`,
  `client/...`, `server/...`, or another explicit path, use that path as given.
- If the user asks to save the polished version, write it under
  `.workspace/posts/` by default.
- Do not overwrite the original file unless the user explicitly asks. Prefer a
  sibling filename such as `<name>.polished.md` when saving a polished version
  without overwrite confirmation.
- If the requested file is missing under `.workspace/posts/`, say that it was
  not found there before searching elsewhere.

## Default Revision Level

Use `light` unless the user requests another level.

| Level | Use for | Allowed changes |
|---|---|---|
| `light` | Default polishing | Fix awkward wording, repeated phrases, sentence rhythm, paragraph breaks, and small transitions. Preserve order and voice as much as possible. |
| `medium` | Messier drafts | Reorder nearby sentences or paragraphs when needed for flow. Preserve all content and emotional direction. |
| `heavy` | Only when explicitly requested | Substantially reshape structure while still adding no new content. Mention that the user's original rhythm may change. |

## Workflow

1. Read the whole text before editing.
2. Identify the central claim, emotional direction, and ending.
3. Preserve those elements while polishing sentence-level flow.
4. Keep intentionally raw phrases when they carry the user's feeling.
5. Ask up to 3 clarification questions instead of guessing if safe polishing is
   not possible.

## Output

If the user asks for only the revised text, output only the polished text.

Otherwise use:

```markdown
## 다듬은 글

[polished text]

## 보존한 점
- ...

## 확인이 필요한 부분
- ...
```

Keep `보존한 점` short. Use `확인이 필요한 부분` only when ambiguity or possible
meaning drift remains.

## Style Guide

- Default voice: Korean, first-person, between diary and column.
- Preserve raw record-like phrasing when the user is describing feelings.
- Prefer natural Korean over ornate or literary expression.
- Reduce filler and repetition, but do not erase personality.
- Keep paragraph breathing room; do not compress everything into dense blocks.
