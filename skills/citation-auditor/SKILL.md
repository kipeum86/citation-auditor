---
name: citation-auditor
description: Audit a markdown file by chunking it, extracting claims with structured output, routing each claim to verifier skills, aggregating verdicts, and rendering annotated markdown.
argument-hint: "<file.md>"
disable-model-invocation: true
---

Audit the markdown file at `$0`.

1. Confirm `$0` exists and is a markdown file. If it does not, stop and ask for a valid path.
2. Run:
   `python -m citation_auditor chunk "$0" --max-tokens 3000`
3. Parse stdout as JSON with the schema `{ "chunks": [...] }`.
4. For each chunk, extract claims using structured output with this schema:
   - `text: string`
   - `sentence_span: { start: integer, end: integer }`
   - `claim_type: factual | citation | quantitative | temporal | other`
   - `suggested_verifier: string | null`
5. Keep claim offsets chunk-relative. Do not convert them to document offsets yourself.
6. Route each claim to verifier skills:
   - If `suggested_verifier` is set and exactly matches a loaded verifier skill name, use it.
   - Otherwise test the claim text against each verifier skill frontmatter `patterns` using case-insensitive regex matching and use every match.
   - If nothing matches, fall back to `general-web`.
7. For each `(claim, verifier)` pair, use the Task tool to dispatch a subagent that loads that verifier skill and receives the claim JSON.
8. Require each verifier subagent to return only this JSON:
   `{ "label": "...", "rationale": "...", "supporting_urls": ["..."], "authority": 0.0 }`
9. Build aggregate input JSON locally:
   - Include the full originating `chunk` object for each claim.
   - Convert each verifier result into a full candidate verdict with:
     - `claim` = extracted claim
     - `verifier_name` = verifier skill name
     - `authority` = returned authority
     - `rationale` = returned rationale
     - `label` = returned label
     - `evidence` = `supporting_urls` mapped to `[{ "url": "<url>" }]`
10. Write that JSON to a temp file and run:
    `python -m citation_auditor aggregate <tmpfile>`
11. Write the aggregate output to a temp file and run:
    `python -m citation_auditor render "$0" <aggfile>`
12. Return only the final annotated markdown unless the user explicitly asked for intermediate JSON.
13. If claim extraction validation fails, retry once with a repair prompt. If it still fails, skip that chunk and note it briefly.
14. If a verifier subagent returns invalid JSON, drop that candidate instead of inventing a verdict.
