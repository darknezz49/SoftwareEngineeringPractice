#!/usr/bin/env bash
# Refresh the Git evidence embedded in docs/GIT_WORKFLOW.md, and write the raw
# evidence files that the technical report references.
#
# Run this at submission time, after the final commit:
#
#     bash docs/refresh_git_evidence.sh
#
set -euo pipefail
cd "$(dirname "$0")/.."        # the script lives in docs/; the repo root is one up

LOG=$(git log --date=short --pretty="%ad  %h  %an  %s")
STAT=$(git log --stat --oneline)
BRANCHES=$(git branch -a)

# raw evidence files, for the report's appendix
{
  echo "# Branch listing"
  echo
  echo '```'
  echo "$BRANCHES"
  echo '```'
  echo
  echo "# Commit history ($(git rev-list --count HEAD) commits)"
  echo
  echo '```'
  echo "$LOG"
  echo '```'
  echo
  echo "# Per-commit file statistics"
  echo
  echo '```'
  echo "$STAT"
  echo '```'
} > docs/GIT_EVIDENCE.md

# keep the workflow document's embedded blocks in step with reality
python3 - "$LOG" "$STAT" <<'PY'
import re
import sys
from pathlib import Path

log, stat = sys.argv[1], sys.argv[2]
p = Path("docs/GIT_WORKFLOW.md")
text = p.read_text(encoding="utf-8")

text = re.sub(r"<!-- GITLOG-START -->.*?<!-- GITLOG-END -->",
              "<!-- GITLOG-START -->\n```\n" + log + "\n```\n"
              "<!-- GITLOG-END -->", text, flags=re.S)
text = re.sub(r"<!-- GITSTAT-START -->.*?<!-- GITSTAT-END -->",
              "<!-- GITSTAT-START -->\n```\n" + stat + "\n```\n"
              "<!-- GITSTAT-END -->", text, flags=re.S)
p.write_text(text, encoding="utf-8")
print("updated docs/GIT_WORKFLOW.md")
PY

echo "wrote docs/GIT_EVIDENCE.md"
echo "commits: $(git rev-list --count HEAD)"
echo "branches:"
printf '  %s\n' $BRANCHES
if [ -n "$(git status --porcelain)" ]; then
  echo
  echo "NOTE: the working tree is dirty; commit before submitting."
  git status --short
fi
