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
metadata:
  patterns:
    - "case-insensitive regex"
  authority: 0.0
disable-model-invocation: true
---
```

Rules:

- `name` must be unique. The primary skill uses it for explicit routing.
- `metadata.patterns` must be regex strings. Routing tests claim text against every pattern case-insensitively.
- `metadata.authority` must be between `0.0` and `1.0`.
- Legacy top-level `patterns` and `authority` are still accepted as a fallback for older third-party verifiers, but new verifier skills should use `metadata`.
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
    "suggested_verifier": "your-verifier-name",
    "audit_reason": "factual"
  },
  "local_only": false
}
```

`sentence_span` values are chunk-relative when they come from the primary skill. Verifier skills should treat them as opaque metadata and should not rewrite them.
`audit_reason` is optional and may be one of `factual`, `citation`, `quantitative`, or `temporal`. Verifiers may ignore it; it exists to explain why a claim entered the audit surface.

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
2. regex `metadata.patterns` match against claim text, with legacy top-level `patterns` as fallback
3. fallback to `general-web`

If multiple skills match by pattern, all of them may run and Python will aggregate the returned verdicts by authority.

## Reference Implementations

The bundled verifiers are concrete examples of the contract above. When designing your own verifier, the closest pattern depends on your data source:

- **Authoritative MCP server**: see [`korean-law`](verifiers/korean-law/SKILL.md) — illustrates how to chain MCP tool calls (statute lookup, precedent search) and turn them into verdict JSON.
- **Free public REST API + canonical-page WebFetch**: see [`us-law`](verifiers/us-law/SKILL.md), [`uk-law`](verifiers/uk-law/SKILL.md), [`eu-law`](verifiers/eu-law/SKILL.md) — illustrates deterministic URL construction, WebFetch as primary path, and **WebSearch fallback** for environments where WebFetch is permission-denied, blocked by anti-bot interstitials, or returns empty bodies on JS-rendered pages.
- **Pure REST metadata APIs (no-auth)**: see [`scholarly`](verifiers/scholarly/SKILL.md) — illustrates how to combine multiple APIs (CrossRef, arXiv, PubMed) under one verifier umbrella.
- **Lightweight summary API + targeted full-article fallback**: see [`wikipedia`](verifiers/wikipedia/SKILL.md) — illustrates a two-tier lookup strategy that minimizes WebFetch volume.
- **Generic WebSearch + WebFetch fallback**: see [`general-web`](verifiers/general-web/SKILL.md) — the catch-all pattern when no domain-specific source exists.
