#!/usr/bin/env bash
# install.sh — Install the ToolHive operator and deploy a starter MCP fleet
#
# Usage:
#   NAMESPACE=platform-tools \
#   GRAFANA_URL=https://your-grafana.internal \
#   GRAFANA_TOKEN=<service-account-token> \
#   ./scripts/toolhive/install.sh
#
# Optional: also deploy GitHub MCP server
#   GITHUB_PAT=<github-pat> ./scripts/toolhive/install.sh
#
# Prerequisites:
#   - kubectl configured for your target cluster
#   - Helm v3.10+
#
# Companion example: examples/toolhive-operator.md
# Blog post: https://www.polarpoint.io/blog/2026/05/15/toolhive-operator/

set -euo pipefail

NAMESPACE="${NAMESPACE:-platform-tools}"
TOOLHIVE_NAMESPACE="${TOOLHIVE_NAMESPACE:-toolhive-system}"
MULTI_TENANT="${MULTI_TENANT:-false}"
GRAFANA_URL="${GRAFANA_URL:-}"
GRAFANA_TOKEN="${GRAFANA_TOKEN:-}"
GITHUB_PAT="${GITHUB_PAT:-}"

echo "==> Installing ToolHive operator"
echo "    Operator namespace : $TOOLHIVE_NAMESPACE"
echo "    MCP fleet namespace: $NAMESPACE"
echo "    Namespace mode     : $MULTI_TENANT"
echo ""

# ── 1. Install CRDs ───────────────────────────────────────────────────────────
echo "==> Step 1/4: Installing ToolHive CRDs"
helm upgrade --install toolhive-operator-crds \
  oci://ghcr.io/stacklok/toolhive/toolhive-operator-crds \
  -n "$TOOLHIVE_NAMESPACE" --create-namespace

echo "    CRDs installed"

# ── 2. Install operator ───────────────────────────────────────────────────────
echo ""
echo "==> Step 2/4: Installing ToolHive operator"

if [ "$MULTI_TENANT" = "true" ]; then
  cat > /tmp/toolhive-values.yaml << EOF
operator:
  rbac:
    scope: 'namespace'
    allowedNamespaces:
      - '${NAMESPACE}'
EOF
  helm upgrade --install toolhive-operator \
    oci://ghcr.io/stacklok/toolhive/toolhive-operator \
    -n "$TOOLHIVE_NAMESPACE" --create-namespace \
    -f /tmp/toolhive-values.yaml
  echo "    Operator installed in namespace mode (allowed: $NAMESPACE)"
else
  helm upgrade --install toolhive-operator \
    oci://ghcr.io/stacklok/toolhive/toolhive-operator \
    -n "$TOOLHIVE_NAMESPACE" --create-namespace
  echo "    Operator installed in cluster mode"
fi

# Wait for operator to be ready
echo "    Waiting for operator pod..."
kubectl rollout status deployment/toolhive-operator \
  -n "$TOOLHIVE_NAMESPACE" --timeout=60s

# ── 3. Create namespace and secrets ──────────────────────────────────────────
echo ""
echo "==> Step 3/4: Setting up fleet namespace"
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

# Create Grafana service account token secret if provided
if [ -n "${GRAFANA_TOKEN}" ]; then
  kubectl create secret generic grafana-token \
    -n "$NAMESPACE" \
    --from-literal=token="$GRAFANA_TOKEN" \
    --dry-run=client -o yaml | kubectl apply -f -
  echo "    Grafana token secret created"
else
  echo "    Skipping Grafana token (set GRAFANA_TOKEN + GRAFANA_URL to enable Grafana MCP server)"
fi

# Create GitHub token secret if PAT provided
if [ -n "${GITHUB_PAT}" ]; then
  kubectl create secret generic github-token \
    -n "$NAMESPACE" \
    --from-literal=token="$GITHUB_PAT" \
    --dry-run=client -o yaml | kubectl apply -f -
  echo "    GitHub token secret created"
else
  echo "    Skipping GitHub token (set GITHUB_PAT to also deploy GitHub MCP server)"
fi

# ── 4. Deploy starter MCP fleet ───────────────────────────────────────────────
echo ""
echo "==> Step 4/4: Deploying starter MCP fleet"

# Grafana MCP server — dashboards, Prometheus, Loki, alerts, OnCall, incidents
if [ -n "${GRAFANA_TOKEN}" ] && [ -n "${GRAFANA_URL}" ]; then
  kubectl apply -f - << EOF
apiVersion: toolhive.stacklok.dev/v1beta1
kind: MCPServer
metadata:
  name: grafana
  namespace: ${NAMESPACE}
spec:
  image: grafana/mcp-grafana:latest
  transport: streamable-http
  mcpPort: 8000
  proxyPort: 8080
  env:
    - name: GRAFANA_URL
      value: "${GRAFANA_URL}"
  secrets:
    - name: grafana-token
      key: token
      targetEnvName: GRAFANA_SERVICE_ACCOUNT_TOKEN
  resources:
    limits:
      cpu: '200m'
      memory: '256Mi'
    requests:
      cpu: '50m'
      memory: '128Mi'
EOF
  echo "    MCPServer/grafana applied"
fi

# GitHub MCP server (only if token available)
if [ -n "${GITHUB_PAT}" ]; then
  kubectl apply -f - << EOF
apiVersion: toolhive.stacklok.dev/v1beta1
kind: MCPServer
metadata:
  name: github
  namespace: ${NAMESPACE}
spec:
  image: ghcr.io/github/github-mcp-server
  transport: stdio
  proxyPort: 8080
  secrets:
    - name: github-token
      key: token
      targetEnvName: GITHUB_PERSONAL_ACCESS_TOKEN
  resources:
    limits:
      cpu: '200m'
      memory: '256Mi'
    requests:
      cpu: '50m'
      memory: '64Mi'
EOF
  echo "    MCPServer/github applied"
fi

if [ -z "${GRAFANA_TOKEN}" ] && [ -z "${GITHUB_PAT}" ]; then
  echo "    No credentials provided — set GRAFANA_TOKEN+GRAFANA_URL or GITHUB_PAT to deploy servers"
  echo "    Operator is installed and ready to manage MCPServer resources."
fi

# ── Status check ─────────────────────────────────────────────────────────────
echo ""
echo "==> Waiting for MCP servers to be ready..."
sleep 10

echo ""
echo "==> Fleet status:"
kubectl get mcpservers -n "$NAMESPACE" 2>/dev/null || \
  echo "    (no MCPServer resources yet — apply manifests from examples/toolhive-operator.md)"

echo ""
echo "==> Done. Next steps:"
echo "    - Check server URLs: kubectl get mcpservers -n $NAMESPACE"
echo "    - Add a VirtualMCPServer to aggregate all backends behind one endpoint"
echo "    - See the full example: examples/toolhive-operator.md"
echo "    - Docs: https://docs.stacklok.com/toolhive/guides-k8s/"
