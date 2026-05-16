#!/usr/bin/env bash
# generate-deck.sh — Generate a sprint review Marp deck from local sample metrics
#
# Usage:
#   ./scripts/marp/generate-deck.sh
#
# This script uses sample-data.json as its data source. For a live ADO/GitHub/Jira
# integration, replace the summarise-metrics.py call with a query against your
# tracker's API (see agents.md for the ADO WIQL approach).
#
# Prerequisites:
#   - Python 3
#   - marp-cli (npm install -g @marp-team/marp-cli) — for HTML output
#
# Companion example: examples/sprint-review-deck.md
# Blog post: https://www.polarpoint.io/blog/2026/03/29/sprint-reviews-with-marp-presentations-as-code/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/output"

mkdir -p "$OUTPUT_DIR"

echo "==> Collecting metrics from sample data"
METRICS=$(python3 "$REPO_ROOT/scripts/metrics/summarise-metrics.py")

REQUESTS=$(echo "$METRICS" | grep requests_total   | awk '{print $2}')
AVG=$(echo "$METRICS"      | grep avg_handled_days | awk '{print $2}')
REQUESTER=$(echo "$METRICS"| grep top_requester    | awk '{print $2}')
TYPE=$(echo "$METRICS"     | grep top_request_type | awk '{print $2}')

SPRINT_DATE=$(date +"%d %B %Y")

echo "==> Generating deck: $OUTPUT_DIR/sprint-review.md"

cat > "$OUTPUT_DIR/sprint-review.md" <<DOC
---
marp: true
theme: default
transition: fade
size: "16:9"
paginate: true
header: "Platform Engineering"
title: "Sprint Review — ${SPRINT_DATE}"
---

<!-- _class: title -->

# Sprint Review
## ${SPRINT_DATE}

---

## Operations Overview

| Metric | Value |
|--------|-------|
| Total requests | ${REQUESTS} |
| Avg resolution time (days) | ${AVG} |
| Top requesting team | ${REQUESTER} |
| Top request category | ${TYPE} |

---

## Request Distribution

_See diagrams/request-distribution.png for the full category breakdown._

---

## Key Insights

- Replace with data-backed observations from Agent 8
- Compare against previous sprint
- Note SLA trend

---

## Next Sprint

- Replace with platform development objectives
- Add demo links and milestone updates

DOC

echo "   Generated: $OUTPUT_DIR/sprint-review.md"

# Render to HTML if marp-cli is installed
if command -v marp &>/dev/null; then
  echo "==> Rendering HTML"
  marp "$OUTPUT_DIR/sprint-review.md" -o "$OUTPUT_DIR/sprint-review.html"
  echo "   Generated: $OUTPUT_DIR/sprint-review.html"
else
  echo "   Skipping HTML render (marp-cli not found — run: npm install -g @marp-team/marp-cli)"
fi

echo ""
echo "==> Done. Next steps:"
echo "    - Open $OUTPUT_DIR/sprint-review.html in a browser"
echo "    - For live data, run agents.md agents against your ADO/GitHub/Jira instance"
echo "    - For PDF: marp $OUTPUT_DIR/sprint-review.md --pdf -o $OUTPUT_DIR/sprint-review.pdf"
echo "    - For PPTX: marp $OUTPUT_DIR/sprint-review.md --pptx -o $OUTPUT_DIR/sprint-review.pptx"
