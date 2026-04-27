---
description: Audit a markdown or DOCX file with citation-auditor.
argument-hint: "[--local-only|--no-web|--offline] <file.md|file.docx>"
disable-model-invocation: true
---

Use the `citation-auditor` skill with the flags and file path provided in `$ARGUMENTS`.

If no path is provided, ask for a markdown or DOCX file path.

Pass `$ARGUMENTS` through unchanged so the skill can parse `--local-only`, `--no-web`, or `--offline`. Markdown inputs return annotated markdown; DOCX inputs create sidecar `.audit.md` and `.audit.json` reports and return their paths plus a concise summary.
