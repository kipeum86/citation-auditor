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
4. For each chunk, extract only factual, citation-bearing claims using structured output with this schema:
   - `text: string`
   - `sentence_span: { start: integer, end: integer }`
   - `claim_type: factual | citation | quantitative | temporal | other`
   - `suggested_verifier: string | null`
5. Do not extract speculation, forecasts, rumors, advocacy, or soft prediction language such as:
   - `전망이다`
   - `예상된다`
   - `업계 관계자에 따르면`
   - `가능성이 있다`
   Unless the sentence also contains a concrete verifiable factual assertion that stands on its own.
6. Keep claim offsets chunk-relative. Do not convert them to document offsets yourself.
7. Route each claim to verifier skills:
   - If `suggested_verifier` is set and exactly matches a loaded verifier skill name, use it.
   - Otherwise test the claim text against each verifier skill frontmatter `patterns` using case-insensitive regex matching and use every match.
   - If nothing matches, fall back to `general-web`.
8. For each `(claim, verifier)` pair, use the Task tool to dispatch a subagent that loads that verifier skill and receives the claim JSON.
9. Require each verifier subagent to return only this JSON:
   `{ "label": "...", "rationale": "...", "supporting_urls": ["..."], "authority": 0.0 }`
10. `supporting_urls` may contain either clickable source URLs or plain-language source references when no stable URL exists. Preserve them verbatim and do not invent clickable URLs for non-linkable sources such as precedent search-result IDs.
11. Build aggregate input JSON locally:
   - Include the full originating `chunk` object for each claim.
   - Convert each verifier result into a full candidate verdict with:
     - `claim` = extracted claim
     - `verifier_name` = verifier skill name
     - `authority` = returned authority
     - `rationale` = returned rationale
     - `label` = returned label
     - `evidence` = `supporting_urls` mapped verbatim to `[{ "url": "<reference>" }]`
12. Write that JSON to a temp file and run:
    `python -m citation_auditor aggregate <tmpfile>`
13. Write the aggregate output to a temp file and run:
    `python -m citation_auditor render "$0" <aggfile>`
14. Return only the final annotated markdown unless the user explicitly asked for intermediate JSON.
15. If claim extraction validation fails, retry once with a repair prompt. If it still fails, skip that chunk and note it briefly.
16. If a verifier subagent returns invalid JSON, drop that candidate instead of inventing a verdict.
17. If a line was skipped because it is a forecast, opinion, rumor, or unattributed speculation, treat that as expected behavior rather than an extraction failure.
18. If the user asks why a forecast or opinion line was not audited, explain that this plugin audits verifiable factual claims and citations, not predictions or commentary.
