#!/usr/bin/env bash
# detect-drift.sh — Query ArgoCD for OutOfSync Applications and produce diff files.
#
# Usage:
#   ARGOCD_SERVER=argocd.example.com ARGOCD_AUTH_TOKEN=<token> bash scripts/detect-drift.sh
#
# Output:
#   /tmp/drift-<app-name>.diff for each OutOfSync Application

set -euo pipefail

ARGOCD_SERVER="${ARGOCD_SERVER:?ARGOCD_SERVER must be set}"
ARGOCD_AUTH_TOKEN="${ARGOCD_AUTH_TOKEN:?ARGOCD_AUTH_TOKEN must be set}"
OUTPUT_DIR="${OUTPUT_DIR:-/tmp}"

echo "=== GitOps Drift Detection ==="
echo "Server: $ARGOCD_SERVER"
echo "Output: $OUTPUT_DIR"
echo ""

# Fetch list of OutOfSync Applications via ArgoCD API
echo "Querying ArgoCD for OutOfSync Applications..."
OUT_OF_SYNC=$(curl -sf \
  -H "Authorization: Bearer $ARGOCD_AUTH_TOKEN" \
  "https://$ARGOCD_SERVER/api/v1/applications?fields=items.metadata.name,items.status.sync.status" \
  | jq -r '.items[] | select(.status.sync.status == "OutOfSync") | .metadata.name')

if [ -z "$OUT_OF_SYNC" ]; then
  echo "No OutOfSync Applications found. All in sync."
  echo "[]" > "$OUTPUT_DIR/drift-apps.json"
  exit 0
fi

echo "OutOfSync Applications:"
echo "$OUT_OF_SYNC" | sed 's/^/  - /'
echo ""

DRIFTED_APPS=()

for APP in $OUT_OF_SYNC; do
  DIFF_FILE="$OUTPUT_DIR/drift-$APP.diff"
  echo "Getting diff for: $APP"

  # Use ArgoCD CLI for diff (requires argocd CLI installed)
  if command -v argocd &>/dev/null; then
    argocd app diff "$APP" \
      --server "$ARGOCD_SERVER" \
      --auth-token "$ARGOCD_AUTH_TOKEN" \
      --grpc-web \
      > "$DIFF_FILE" 2>&1 || true
  else
    # Fallback: use ArgoCD API
    curl -sf \
      -H "Authorization: Bearer $ARGOCD_AUTH_TOKEN" \
      "https://$ARGOCD_SERVER/api/v1/applications/$APP/resource-tree" \
      > "$DIFF_FILE" 2>&1 || echo "Could not get diff for $APP" > "$DIFF_FILE"
  fi

  if [ -s "$DIFF_FILE" ]; then
    echo "  Diff saved: $DIFF_FILE ($(wc -c < "$DIFF_FILE") bytes)"
    DRIFTED_APPS+=("$APP")
  else
    echo "  No diff content for $APP (may be sync timing issue)"
    rm -f "$DIFF_FILE"
  fi
done

# Write summary JSON for downstream scripts
printf '%s\n' "${DRIFTED_APPS[@]}" | jq -R . | jq -s . > "$OUTPUT_DIR/drift-apps.json"

echo ""
echo "=== Detection Complete ==="
echo "Applications with drift: ${#DRIFTED_APPS[@]}"
echo "Diff files in: $OUTPUT_DIR"
echo "App list: $OUTPUT_DIR/drift-apps.json"
