#!/usr/bin/env bash
set -euo pipefail

mkdir -p scripts/marp/output

METRICS=$(python3 scripts/metrics/summarise-metrics.py)

REQUESTS=$(echo "$METRICS" | grep requests_total | awk '{print $2}')
AVG=$(echo "$METRICS" | grep avg_handled_days | awk '{print $2}')
REQUESTER=$(echo "$METRICS" | grep top_requester | awk '{print $2}')
TYPE=$(echo "$METRICS" | grep top_request_type | awk '{print $2}')

cat > scripts/marp/output/sprint-review.md <<DOC
---
marp: true
title: Sprint Review
---

# Sprint Review

---

## Requests
- Total: ${REQUESTS}
- Avg time to handle (days): ${AVG}

---

## Top Requester
- ${REQUESTER}

---

## Top Request Type
- ${TYPE}

DOC

# Optional: if marp-cli is installed
# marp scripts/marp/output/sprint-review.md -o scripts/marp/output/sprint-review.html

echo "Generated scripts/marp/output/sprint-review.md"
