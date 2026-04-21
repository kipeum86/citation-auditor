# Verifier Skills

Third-party verifier skills extend citation-auditor without changing the Python package.

## Layout

Use the Claude Code docs-compliant layout:

- `skills/<your-skill-name>/SKILL.md`

## Required Frontmatter

Each verifier skill must declare:

```yaml
---
name: your-verifier-name
description: Short summary of what the verifier checks.
patterns:
  - "case-insensitive regex"
authority: 0.0
disable-model-invocation: true
---
```

Rules:

- `name` must be unique. The primary skill uses it for explicit routing.
- `patterns` must be regex strings. Routing tests claim text against every pattern case-insensitively.
- `authority` must be between `0.0` and `1.0`.
- Higher authority wins during aggregation. Equal-authority conflicts resolve to `unknown`.

## Input Contract

Verifier skills should accept either:

- a bare `Claim` JSON object, or
- an object shaped like:

```json
{
  "claim": {
    "text": "string",
    "sentence_span": { "start": 0, "end": 10 },
    "claim_type": "factual",
    "suggested_verifier": "your-verifier-name"
  },
  "local_only": false
}
```

`sentence_span` values are chunk-relative when they come from the primary skill. Verifier skills should treat them as opaque metadata and should not rewrite them.

## Output Contract

Return only JSON in this exact shape:

```json
{
  "label": "verified|contradicted|unknown",
  "rationale": "string",
  "supporting_urls": ["https://example.com"],
  "authority": 0.0
}
```

Notes:

- `authority` in the output should match the frontmatter authority.
- `supporting_urls` may be empty if the verifier cannot reach a conclusion.
- `supporting_urls` may contain either clickable URLs or plain-language source references when no stable URL exists.
- Final-user rationales should read like professional review notes, not internal release or task-tracking jargon.
- Do not emit markdown fences or explanatory prose around the JSON.

## Routing Behavior

The primary `citation-auditor` skill routes claims in this order:

1. `suggested_verifier` exact match by skill `name`
2. regex `patterns` match against claim text
3. fallback to `general-web`

If multiple skills match by pattern, all of them may run and Python will aggregate the returned verdicts by authority.
