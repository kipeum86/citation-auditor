---
description: Audit a markdown or DOCX file with citation-auditor.
argument-hint: "<file.md|file.docx>"
disable-model-invocation: true
---

Use the `citation-auditor` skill with the file path provided in `$ARGUMENTS`.

If no path is provided, ask for a markdown or DOCX file path.

Pass the path through unchanged. Markdown inputs return annotated markdown; DOCX inputs create sidecar `.audit.md` and `.audit.json` reports and return their paths plus a concise summary.
