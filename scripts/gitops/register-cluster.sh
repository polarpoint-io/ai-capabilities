#!/usr/bin/env bash
# register-cluster.sh — Register a Kubernetes cluster with ArgoCD via the cluster label secret pattern.
#
# Creates a Kubernetes secret in the argocd namespace with the argocd.argoproj.io/secret-type=cluster
# label and the metadata labels that ApplicationSet cluster generators filter on.
#
# Usage:
#   bash scripts/gitops/register-cluster.sh \
#     --name prod-eu \
#     --server https://prod-eu.k8s.example.com \
#     --environment production \
#     --region eu \
#     --tier critical
#
# Options:
#   --name          Cluster name (used as secret name and argocd cluster display name)
#   --server        Kubernetes API server URL
#   --environment   Cluster environment label (e.g. production, staging, dev)
#   --region        Cluster region label (e.g. eu, us, apac)
#   --tier          Cluster tier label (e.g. critical, standard)
#   --namespace     ArgoCD namespace (default: argocd)
#   --kubeconfig    Path to a specific kubeconfig for the target cluster
#                   (if omitted, uses current context for credential extraction)
#   --dry-run       Print the secret YAML without applying it
#
# Environment variables:
#   ARGOCD_NAMESPACE   ArgoCD namespace (default: argocd)
#   KUBECONFIG         Standard kubeconfig path
#
# Requires:
#   kubectl, base64, jq (optional — for credential inspection)

set -euo pipefail

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

NAME=""
SERVER=""
ENVIRONMENT=""
REGION=""
TIER="standard"
NAMESPACE="${ARGOCD_NAMESPACE:-argocd}"
DRY_RUN=false
TARGET_KUBECONFIG=""

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

usage() {
  grep '^#' "$0" | grep -v '^#!/' | sed 's/^# \{0,1\}//'
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --name)          NAME="$2";              shift 2 ;;
    --server)        SERVER="$2";            shift 2 ;;
    --environment)   ENVIRONMENT="$2";       shift 2 ;;
    --region)        REGION="$2";            shift 2 ;;
    --tier)          TIER="$2";              shift 2 ;;
    --namespace)     NAMESPACE="$2";         shift 2 ;;
    --kubeconfig)    TARGET_KUBECONFIG="$2"; shift 2 ;;
    --dry-run)       DRY_RUN=true;           shift ;;
    -h|--help)       usage ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

errors=()
[[ -z "$NAME" ]]        && errors+=("--name is required")
[[ -z "$SERVER" ]]      && errors+=("--server is required")
[[ -z "$ENVIRONMENT" ]] && errors+=("--environment is required")
[[ -z "$REGION" ]]      && errors+=("--region is required")

if [[ ${#errors[@]} -gt 0 ]]; then
  echo "ERROR: Missing required arguments:" >&2
  for e in "${errors[@]}"; do echo "  $e" >&2; done
  echo "" >&2
  echo "Run with --help for usage." >&2
  exit 1
fi

# Validate environment value
valid_envs=("dev" "staging" "production")
valid=false
for e in "${valid_envs[@]}"; do [[ "$ENVIRONMENT" == "$e" ]] && valid=true; done
if [[ "$valid" == false ]]; then
  echo "WARNING: --environment '$ENVIRONMENT' is not one of: ${valid_envs[*]}" >&2
fi

# ---------------------------------------------------------------------------
# Extract credentials from target cluster
# ---------------------------------------------------------------------------

echo "==> Extracting credentials for cluster: $NAME"

# Determine the kubeconfig to use for credential extraction
KUBE_ARGS=""
if [[ -n "$TARGET_KUBECONFIG" ]]; then
  KUBE_ARGS="--kubeconfig $TARGET_KUBECONFIG"
  echo "    Using kubeconfig: $TARGET_KUBECONFIG"
fi

# Get the cluster CA certificate
CA_DATA=$(kubectl $KUBE_ARGS config view --raw -o jsonpath='{.clusters[0].cluster.certificate-authority-data}' 2>/dev/null || true)

if [[ -z "$CA_DATA" ]]; then
  echo "    WARNING: Could not extract CA data from kubeconfig — using placeholder" >&2
  CA_DATA="<base64-encoded-ca-cert>"
fi

# Build a service account token or bearer token
# In production: create a dedicated ArgoCD service account in the target cluster
# Here we extract from the current context for demonstration
TOKEN=$(kubectl $KUBE_ARGS config view --raw -o jsonpath='{.users[0].user.token}' 2>/dev/null || true)

if [[ -z "$TOKEN" ]]; then
  echo "    WARNING: Could not extract token from kubeconfig" >&2
  echo "    For production: create a dedicated service account in $NAME and use its token" >&2
  TOKEN="<service-account-token>"
fi

# ---------------------------------------------------------------------------
# Build the ArgoCD cluster secret config JSON
# ---------------------------------------------------------------------------

# ArgoCD stores cluster config as a JSON blob in the secret's 'config' field
CONFIG_JSON=$(cat <<JSON
{
  "bearerToken": "${TOKEN}",
  "tlsClientConfig": {
    "insecure": false,
    "caData": "${CA_DATA}"
  }
}
JSON
)

CONFIG_B64=$(echo -n "$CONFIG_JSON" | base64 | tr -d '\n')
NAME_B64=$(echo -n "$NAME" | base64 | tr -d '\n')
SERVER_B64=$(echo -n "$SERVER" | base64 | tr -d '\n')

# ---------------------------------------------------------------------------
# Render secret YAML
# ---------------------------------------------------------------------------

SECRET_YAML=$(cat <<YAML
apiVersion: v1
kind: Secret
metadata:
  name: cluster-${NAME}
  namespace: ${NAMESPACE}
  labels:
    argocd.argoproj.io/secret-type: cluster
    environment: ${ENVIRONMENT}
    region: ${REGION}
    tier: ${TIER}
  annotations:
    registered-by: register-cluster.sh
    registered-at: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
type: Opaque
data:
  name: ${NAME_B64}
  server: ${SERVER_B64}
  config: ${CONFIG_B64}
YAML
)

# ---------------------------------------------------------------------------
# Apply or print
# ---------------------------------------------------------------------------

if [[ "$DRY_RUN" == true ]]; then
  echo ""
  echo "==> DRY RUN — secret YAML (not applied):"
  echo "---"
  echo "$SECRET_YAML"
  echo "---"
  echo ""
  echo "Run without --dry-run to apply."
  exit 0
fi

echo ""
echo "==> Applying secret to namespace '${NAMESPACE}'..."
echo "$SECRET_YAML" | kubectl apply -f -

echo ""
echo "==> Cluster registered successfully."
echo ""
echo "    Cluster name:    $NAME"
echo "    Server:          $SERVER"
echo "    Environment:     $ENVIRONMENT"
echo "    Region:          $REGION"
echo "    Tier:            $TIER"
echo ""
echo "Next steps:"
echo "  1. Create clusters/${NAME}/values.yaml in Git (if using per-cluster values)"
echo "  2. ApplicationSets with matching label selectors will deploy automatically"
echo "  3. Verify with: argocd app list --selector environment=${ENVIRONMENT}"
