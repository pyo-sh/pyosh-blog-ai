---
id: "020"
title: "OpenAI --output-schema requires all properties in required array"
date: "2026-03-14"
tags: ["#codex #openai #structured-output #schema #json-schema"]
---

# Findings 020 - OpenAI --output-schema requires all properties in required array

## Context

Codex review dispatch was failing with `400 invalid_json_schema` on every call. The error message was:

```
In context=('properties', 'issues', 'items'),
'required' is required to be supplied and to be an array including every key in properties.
Missing 'path'.
```

The failure happened before codex executed any code, producing a 0-byte output file and `rc=1`.

## Finding

OpenAI's structured output / `--output-schema` feature enforces a stricter superset of JSON Schema draft-07. Specifically:

**Every key declared in `properties` must also appear in `required`.** Optional fields are expressed as nullable unions, not by omission from `required`.

Standard JSON Schema allows properties to be absent from `required` (making them optional). OpenAI rejects this - the schema must be "fully strict": all properties required, nullable via type union.

### Correct pattern

```json
{
  "required": ["severity", "path", "line", "title", "body"],
  "properties": {
    "path": { "type": ["string", "null"], "description": "null if not file-specific." },
    "line": { "type": ["integer", "null"], "description": "null if not applicable." }
  }
}
```

### Incorrect pattern (causes 400)

```json
{
  "required": ["severity", "title", "body"],
  "properties": {
    "path": { "type": "string", "maxLength": 500 },
    "line": { "type": "integer", "minimum": 1 }
  }
}
```

## Additional constraints observed

- `maxLength` and `minimum` on nullable union types may also cause rejection. Remove them from nullable fields; enforce downstream in application code.
- The error surfaces at schema validation time, not at model inference time - the request never reaches the model.
- `codex exec --output-schema` (generic) supports `--output-last-message`; `codex exec review --base` does not.

## Impact on downstream validator

When fields become required-but-nullable, downstream validators must be updated:

- `if "line" in item` - always true when codex outputs `{"line": null}`, but `isinstance(None, int)` is False, causing a spurious validation error. Fix: `if "line" in item and item["line"] is not None`.
- `item.get("path", "")` - returns `None` (not `""`) when the key is present with a null value. Fix: `item.get("path") or ""`.

## References

- PR #203
- `.agents/skills/dev-pipeline/scripts/dev_pipeline/review_schema.json`
- `.agents/skills/dev-review/scripts/review_publish.py`
