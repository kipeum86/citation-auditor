---
name: citation-auditor
description: Audit a markdown or DOCX file by chunking extracted audit text, verifying claims, aggregating verdicts, and rendering annotated markdown or an external audit report.
argument-hint: "[--local-only|--no-web|--offline] <file.md|file.docx>"
disable-model-invocation: true
---

Audit the markdown or DOCX file described by `$ARGUMENTS`.

1. Parse `$ARGUMENTS` into optional flags and one file path.
   - Recognized local-only flags: `--local-only`, `--no-web`, `--offline`.
   - If any recognized local-only flag is present, set `local_only` to `true`; otherwise set `local_only` to `false`.
   - Do not infer `local_only` from natural-language sensitivity words alone. If the user mentions a sensitive, private, privileged, confidential, PHI, PII, 민감, 비밀, or 특권 document but did not pass one of the recognized flags, pause before auditing and ask whether to rerun with `--local-only`.
   - If an unknown flag is present, stop and ask for a valid flag or a plain file path.
   - If there is not exactly one file path after removing recognized flags, ask for one markdown or DOCX file path.
2. Confirm the file path exists and has extension `.md`, `.markdown`, or `.docx`. If it does not, stop and ask for a valid markdown or DOCX path.
   - If the file is `.md` or `.markdown`, use it as the audit input and use markdown mode.
   - If the file is `.docx`, create two temporary paths for audit-source markdown and source map JSON, then run:
     `python -m citation_auditor extract-docx "<file-path>" --out-md <tmp-source.md> --out-map <tmp-map.json>`
     Use `<tmp-source.md>` as the audit input, remember `<tmp-map.json>` as the source map, and use DOCX report mode. The original DOCX must remain untouched.
3. Run `python -m citation_auditor chunk <audit-input> --max-tokens 3000`, where `<audit-input>` is the original file in markdown mode and `<tmp-source.md>` in DOCX report mode.
4. Parse stdout as JSON with the schema `{ "chunks": [...] }`.
5. For each chunk, extract verifiable factual claims and citation-bearing claims using structured output with this schema:
   - `text: string`
   - `sentence_span: { start: integer, end: integer }`
   - `claim_type: factual | citation | quantitative | temporal | other`
   - `suggested_verifier: string | null`
   - `audit_reason: factual | citation | quantitative | temporal | null`
   Include concrete factual assertions even when no citation is attached, especially:
   - dates and effective dates
   - numeric claims
   - named legal authority or institutional action
   - existence or non-existence of a statute, case, agency act, paper, organization, or person
6. Do not extract speculation, forecasts, rumors, advocacy, or soft prediction language such as:
   - `전망이다`
   - `예상된다`
   - `업계 관계자에 따르면`
   - `가능성이 있다`
   Unless the sentence also contains a concrete verifiable factual assertion that stands on its own.
7. Keep claim offsets chunk-relative. Do not convert them to document offsets yourself.
8. Route each claim to verifier skills:
   - If `suggested_verifier` is set and exactly matches a loaded verifier skill name, use it.
   - Otherwise test the claim text against each verifier skill frontmatter `metadata.patterns` using case-insensitive regex matching and use every match.
   - For backward compatibility with older third-party verifier skills, if `metadata.patterns` is absent, fall back to top-level frontmatter `patterns`.
   - If nothing matches, fall back to `general-web`.
9. For each `(claim, verifier)` pair, use the Task tool to dispatch a subagent that loads that verifier skill and receives `{ "claim": <claim JSON>, "local_only": <local_only> }`. DOCX mode uses the same verifier payload rule as markdown mode.
10. Require each verifier subagent to return only this JSON:
   `{ "label": "...", "rationale": "...", "supporting_urls": ["..."], "authority": 0.0 }`
11. `supporting_urls` may contain either clickable source URLs or plain-language source references when no stable URL exists. Preserve them verbatim and do not invent clickable URLs for non-linkable sources such as precedent search-result IDs.
12. Build aggregate input JSON locally. The exact top-level shape is `{ "verdicts": [ <bundle>, ... ] }` where each `<bundle>` covers one `(chunk, claim)` pair and holds all verifier candidates for that claim. Do not invent other top-level keys.

    **Exact schema (copy this structure):**
    ```json
    {
      "verdicts": [
        {
          "chunk": { "index": 0, "text": "<full chunk text>", "segments": [ { "chunk_start": 0, "chunk_end": 44, "document_start": 0, "document_end": 44 } ] },
          "claim": { "text": "<claim sentence>", "sentence_span": { "start": 64, "end": 268 }, "claim_type": "citation", "suggested_verifier": "us-law", "audit_reason": "citation" },
          "candidates": [
            {
              "claim": { "text": "<same claim as above>", "sentence_span": { "start": 64, "end": 268 }, "claim_type": "citation", "suggested_verifier": "us-law", "audit_reason": "citation" },
              "verifier_name": "us-law",
              "authority": 0.9,
              "label": "contradicted",
              "rationale": "<Korean rationale from verifier>",
              "evidence": [ { "url": "https://..." } ]
            }
          ]
        }
      ]
    }
    ```

    Rules:
    - One bundle per `(chunk, claim)` pair. If the same claim has two verifiers, put both candidates inside the same bundle's `candidates` array — do NOT create a second bundle for the same claim.
    - The top-level `claim` inside each bundle is the canonical claim; each candidate's `claim` must match it verbatim.
    - `audit_reason` is optional for backward compatibility, but include it whenever claim extraction produced it.
    - `evidence` items require a non-empty `url` string. If the verifier returned `supporting_urls: []`, emit `"evidence": []` — do not emit `[{"url": ""}]`.
    - `label` must be one of `verified` / `contradicted` / `unknown`.
    - `authority` must match the verifier skill's declared `metadata.authority` value. For older third-party verifier skills, top-level frontmatter `authority` is an accepted fallback.

13. Write that JSON to a temp file and run:
    `python -m citation_auditor aggregate <tmpfile>`
14. Write the aggregate output to a temp file. Then:
    - In markdown mode, run:
      `python -m citation_auditor render "<file-path>" <aggfile>`
    - In DOCX report mode, write reports beside the original DOCX using the same basename plus `.audit.md` and `.audit.json`, then run:
      `python -m citation_auditor report <tmp-map.json> <aggfile> --out <original-basename>.audit.md --out-json <original-basename>.audit.json`
15. Return:
    - In markdown mode, only the final annotated markdown unless the user explicitly asked for intermediate JSON.
    - In DOCX report mode, only the generated `.audit.md` and `.audit.json` paths plus a concise Summary table from the markdown report. Do not paste the full report into chat unless the user explicitly asks for it.
16. If claim extraction validation fails, retry once with a repair prompt. If it still fails, skip that chunk and note it briefly.
17. If a verifier subagent returns invalid JSON, drop that candidate instead of inventing a verdict.
18. If a line was skipped because it is a forecast, opinion, rumor, or unattributed speculation, treat that as expected behavior rather than an extraction failure.
19. If the user asks why a forecast or opinion line was not audited, explain that this plugin audits verifiable factual claims and citations, not predictions or commentary.
