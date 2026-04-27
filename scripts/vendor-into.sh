#!/usr/bin/env bash
# vendor-into.sh — copy citation-auditor into another CC-based project as local skills.
#
# Why this exists:
#   The v1.0–v1.2 plugin path (/plugin marketplace add ...) has a CC cache drift pain.
#   This script lets you pin a specific citation-auditor version directly inside another
#   repo's .claude/ directory, so "git clone + CC open" is enough. No plugin install,
#   no cache refresh, no version ambiguity — git log shows the exact pinned version.
#
# Usage:
#   ./scripts/vendor-into.sh <path-to-target-repo> [--no-python] [--dry-run] [--confirm-docx-upgrade]
#
# What gets copied (into <target>):
#   commands/audit.md              → <target>/.claude/commands/audit.md
#   skills/citation-auditor/       → <target>/.claude/skills/citation-auditor/
#   skills/verifiers/              → <target>/.claude/skills/verifiers/
#   skills/README.md               → <target>/.claude/skills/README.md
#   citation_auditor/*.py          → <target>/citation_auditor/   (Python utility, unless --no-python)
#   VENDOR.md                      → <target>/.claude/skills/citation-auditor/VENDOR.md  (version stamp)
#
# What does NOT happen automatically (printed as instructions instead):
#   - Merging pyproject.toml dependencies into target's pyproject.toml.
#     Reason: TOML merge is fragile and target's style (uv, poetry, hatch, setuptools) varies.
#     Script prints the required deps for you to paste.
#   - Merging .claude/settings.json WebFetch allowlists.
#     Reason: target may already have allowlists we should not overwrite.
#     Script prints the allowlist for you to add.
#
# Flags:
#   --no-python   Skip copying the citation_auditor/ Python package (if target already has it
#                 as a git dep or you intend to install it separately).
#   --dry-run     Show what would be copied without making changes.
#   --confirm-docx-upgrade
#                 Required when applying v1.4+ over an existing v1.3 vendored copy.

set -euo pipefail

# ---- args ----
TARGET=""
NO_PYTHON=0
DRY_RUN=0
CONFIRM_DOCX_UPGRADE=0

for arg in "$@"; do
  case "$arg" in
    --no-python) NO_PYTHON=1 ;;
    --dry-run)   DRY_RUN=1 ;;
    --confirm-docx-upgrade) CONFIRM_DOCX_UPGRADE=1 ;;
    -h|--help)
      sed -n '2,35p' "$0" | sed 's/^# //; s/^#//'
      exit 0
      ;;
    -*)
      echo "Unknown flag: $arg" >&2
      echo "Run with --help for usage." >&2
      exit 2
      ;;
    *)
      if [ -z "$TARGET" ]; then
        TARGET="$arg"
      else
        echo "Unexpected extra argument: $arg" >&2
        exit 2
      fi
      ;;
  esac
done

if [ -z "$TARGET" ]; then
  echo "Usage: $0 <path-to-target-repo> [--no-python] [--dry-run] [--confirm-docx-upgrade]" >&2
  exit 2
fi

# ---- locate source ----
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SOURCE="$( cd "$SCRIPT_DIR/.." && pwd )"

if [ ! -f "$SOURCE/.claude-plugin/plugin.json" ]; then
  echo "Error: expected $SOURCE/.claude-plugin/plugin.json — this script must run from inside the citation-auditor repo." >&2
  exit 1
fi

if [ ! -d "$TARGET" ]; then
  echo "Error: target directory does not exist: $TARGET" >&2
  exit 1
fi

# Resolve absolute target
TARGET="$( cd "$TARGET" && pwd )"

# Prevent vendoring into self
if [ "$TARGET" = "$SOURCE" ]; then
  echo "Error: target must be a different repository than the citation-auditor source." >&2
  exit 1
fi

# Read version from plugin.json (no jq dep — simple grep, BSD/GNU sed compatible)
VERSION="$( grep -E '"version"[[:space:]]*:' "$SOURCE/.claude-plugin/plugin.json" | head -1 | sed -E 's/.*"version"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/' )"
if [ -z "$VERSION" ]; then
  echo "Error: could not read version from $SOURCE/.claude-plugin/plugin.json" >&2
  exit 1
fi

TARGET_VENDOR_STAMP="$TARGET/.claude/skills/citation-auditor/VENDOR.md"
EXISTING_VENDOR_VERSION=""
if [ -f "$TARGET_VENDOR_STAMP" ]; then
  EXISTING_VENDOR_VERSION="$(
    grep -E '^- Version:[[:space:]]*' "$TARGET_VENDOR_STAMP" 2>/dev/null \
      | head -1 \
      | sed -E 's/.*v?([0-9]+[.][0-9]+[.][0-9]+).*/\1/' \
      || true
  )"
fi

version_ge_1_4() {
  local version="$1"
  local major minor
  if [[ ! "$version" =~ ^([0-9]+)[.]([0-9]+)[.]([0-9]+) ]]; then
    return 1
  fi
  major="${BASH_REMATCH[1]}"
  minor="${BASH_REMATCH[2]}"
  if [ "$major" -gt 1 ]; then
    return 0
  fi
  if [ "$major" -eq 1 ] && [ "$minor" -ge 4 ]; then
    return 0
  fi
  return 1
}

SOURCE_HAS_DOCX_BEHAVIOR=0
if version_ge_1_4 "$VERSION"; then
  SOURCE_HAS_DOCX_BEHAVIOR=1
fi

TARGET_IS_V13_VENDOR=0
case "$EXISTING_VENDOR_VERSION" in
  1.3.*) TARGET_IS_V13_VENDOR=1 ;;
esac

# Check rsync
if ! command -v rsync >/dev/null 2>&1; then
  echo "Error: rsync not found on PATH." >&2
  exit 1
fi

# ---- plan the copy ----
echo "citation-auditor vendor"
echo "  source:  $SOURCE"
echo "  target:  $TARGET"
echo "  version: v$VERSION"
if [ -n "$EXISTING_VENDOR_VERSION" ]; then
  echo "  current: v$EXISTING_VENDOR_VERSION"
else
  echo "  current: none"
fi
echo "  python:  $( [ "$NO_PYTHON" = "1" ] && echo 'SKIP (--no-python)' || echo 'include' )"
echo "  mode:    $( [ "$DRY_RUN" = "1" ] && echo 'dry-run' || echo 'apply' )"
if [ "$SOURCE_HAS_DOCX_BEHAVIOR" = "1" ]; then
  echo "  docx:    DOCX behavior will be enabled in the vendored skill."
fi
echo

if [ "$SOURCE_HAS_DOCX_BEHAVIOR" = "1" ] && [ "$TARGET_IS_V13_VENDOR" = "1" ]; then
  cat >&2 <<EOF
Warning: target is currently vendored at v${EXISTING_VENDOR_VERSION}, and v${VERSION} enables DOCX audit behavior.
Recommended rollout: update one canary legal-agent repo first, verify markdown regression and DOCX audit behavior, then update other repos deliberately.
EOF
  if [ "$DRY_RUN" = "1" ]; then
    echo "Dry-run only: applying this upgrade would require --confirm-docx-upgrade." >&2
  elif [ "$CONFIRM_DOCX_UPGRADE" = "0" ]; then
    echo "Error: rerun with --confirm-docx-upgrade to apply this v1.3 -> v${VERSION} vendor upgrade." >&2
    exit 2
  else
    echo "DOCX upgrade confirmation received; proceeding with canary-aware vendor update." >&2
  fi
  echo
fi

RSYNC_FLAGS=(-a --delete-excluded --exclude='__pycache__' --exclude='*.pyc')
if [ "$DRY_RUN" = "1" ]; then
  RSYNC_FLAGS+=(--dry-run -v)
fi

# ---- apply copy ----
run() {
  echo "  $*"
  if [ "$DRY_RUN" = "0" ]; then
    eval "$@"
  fi
}

run "mkdir -p \"$TARGET/.claude/commands\""
run "mkdir -p \"$TARGET/.claude/skills\""

# commands/audit.md
run "rsync ${RSYNC_FLAGS[*]} \"$SOURCE/commands/audit.md\" \"$TARGET/.claude/commands/audit.md\""

# skills (orchestration + verifiers + README)
run "rsync ${RSYNC_FLAGS[*]} \"$SOURCE/skills/citation-auditor/\" \"$TARGET/.claude/skills/citation-auditor/\""
run "rsync ${RSYNC_FLAGS[*]} \"$SOURCE/skills/verifiers/\" \"$TARGET/.claude/skills/verifiers/\""
run "rsync ${RSYNC_FLAGS[*]} \"$SOURCE/skills/README.md\" \"$TARGET/.claude/skills/README.md\""

# Python package (optional)
if [ "$NO_PYTHON" = "0" ]; then
  run "rsync ${RSYNC_FLAGS[*]} \"$SOURCE/citation_auditor/\" \"$TARGET/citation_auditor/\""
fi

# VENDOR.md stamp (always fresh, overwritten on every run)
VENDOR_STAMP="$TARGET/.claude/skills/citation-auditor/VENDOR.md"
TIMESTAMP="$( date -u +%Y-%m-%dT%H:%M:%SZ )"
SOURCE_COMMIT="$( cd "$SOURCE" && git rev-parse --short HEAD 2>/dev/null || echo unknown )"
SOURCE_TAG="$( cd "$SOURCE" && git describe --tags --exact-match 2>/dev/null || echo "no-exact-tag" )"

STAMP_CONTENT="# citation-auditor vendor stamp

This directory was populated by \`scripts/vendor-into.sh\` from the citation-auditor repo.

- Version: **v${VERSION}**
- Source commit: ${SOURCE_COMMIT}
- Source tag:    ${SOURCE_TAG}
- Vendored at:   ${TIMESTAMP}
- Target:        ${TARGET}

To update this vendor copy, run \`./scripts/vendor-into.sh ${TARGET}\` from the citation-auditor repo (latest version).

Do not hand-edit files under \`.claude/skills/citation-auditor/\` or \`.claude/skills/verifiers/\` — they will be overwritten on the next vendor run. If you need to customize a verifier, copy it to a new folder under \`.claude/skills/verifiers/my-<name>/\` instead.
"

if [ "$DRY_RUN" = "1" ]; then
  echo "  [dry-run] would write $VENDOR_STAMP"
else
  printf '%s' "$STAMP_CONTENT" > "$VENDOR_STAMP"
  echo "  wrote $VENDOR_STAMP"
fi

# ---- post-copy instructions ----
echo
echo "=== Vendor copy complete ==="
echo

cat <<'EOF'
=== Manual steps (if you haven't done them yet) ===

1. pyproject.toml — add these deps to your target project (uv/poetry/hatch/etc.):

     marko>=2.1.0
     pydantic>=2.7.0

   Then run `uv sync` (or your package manager's equivalent) in the target repo.

2. WebFetch allowlist — if you use CC and want subagents to fetch verifier sources
   without permission prompts, add to <target>/.claude/settings.json under
   "permissions.allow":

     "WebFetch(domain:law.cornell.edu)"
     "WebFetch(domain:courtlistener.com)"
     "WebFetch(domain:www.courtlistener.com)"
     "WebFetch(domain:bailii.org)"
     "WebFetch(domain:www.bailii.org)"
     "WebFetch(domain:legislation.gov.uk)"
     "WebFetch(domain:www.legislation.gov.uk)"
     "WebFetch(domain:eur-lex.europa.eu)"
     "WebFetch(domain:api.crossref.org)"
     "WebFetch(domain:export.arxiv.org)"
     "WebFetch(domain:arxiv.org)"
     "WebFetch(domain:eutils.ncbi.nlm.nih.gov)"
     "WebFetch(domain:en.wikipedia.org)"
     "WebFetch(domain:ko.wikipedia.org)"

3. Commit the vendored files:

     git add .claude/ citation_auditor/ pyproject.toml uv.lock
     git commit -m "vendor: citation-auditor v<VERSION>"

4. Open the target repo in Claude Code. The slash command
   /citation-auditor:audit <file.md|file.docx> will be available.
EOF

# Substitute version into the instructions above (rough, but works for the commit line)
echo
echo "(Current vendored version: v${VERSION})"
echo
