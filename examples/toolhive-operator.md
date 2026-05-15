# Example: ToolHive Operator — MCP Fleet Management

**Goal:** Deploy and manage a fleet of MCP servers in Kubernetes using the ToolHive operator — automatic RBAC, secret injection, multi-tenant namespace scoping, and a VirtualMCPServer aggregating all backends behind a single endpoint.

Related blog post: [MCP Servers in Kubernetes: The ToolHive Operator](https://www.polarpoint.io/blog/2026/05/15/toolhive-operator/)

## Problem

Running MCP servers in Kubernetes without an operator means re-implementing auth, RBAC, secret injection, and lifecycle management for every server by hand. The ToolHive operator gives you all of that as declarative CRDs that fit into your existing GitOps workflow.

## What this example covers

- Installing the ToolHive operator CRDs and controller via Helm
- `MCPServer` resources for in-cluster servers (GitHub MCP, Kubernetes MCP, OSV)
- `MCPRemoteProxy` for external SaaS MCP endpoints
- Secret injection from Kubernetes secrets and External Secrets Operator
- `VirtualMCPServer` aggregating all backends behind one endpoint
- Namespace mode for multi-tenant isolation
- ArgoCD Application syncing the fleet declaratively

## Prerequisites

- Kubernetes cluster (current or two previous minor versions)
- Helm v3.10+
- `kubectl` configured for your cluster
- Optional: ArgoCD for GitOps reconciliation

## Install the operator

```bash
# Step 1: CRDs (install first, upgrade separately)
helm upgrade --install toolhive-operator-crds \
  oci://ghcr.io/stacklok/toolhive/toolhive-operator-crds \
  -n toolhive-system --create-namespace

# Step 2: Operator controller
helm upgrade --install toolhive-operator \
  oci://ghcr.io/stacklok/toolhive/toolhive-operator \
  -n toolhive-system --create-namespace

# Verify
kubectl get pods -n toolhive-system
kubectl get crd | grep toolhive
```

For multi-tenant clusters, use namespace mode (`values.yaml`):

```yaml
operator:
  rbac:
    scope: 'namespace'
    allowedNamespaces:
      - 'platform-tools'
      - 'team-frontend'
      - 'team-backend'
```

```bash
helm upgrade --install toolhive-operator \
  oci://ghcr.io/stacklok/toolhive/toolhive-operator \
  -n toolhive-system -f values.yaml
```

## MCPServer: Grafana MCP

Exposes Grafana dashboards, Prometheus queries, Loki log searches, alert rules, Grafana OnCall schedules, and incident management as MCP tools. A natural fit for any platform team running Grafana.

```bash
# Create a Grafana service account token first
kubectl -n platform-tools create secret generic grafana-token \
  --from-literal=token=<GRAFANA_SERVICE_ACCOUNT_TOKEN>
```

```yaml
# mcp-servers/grafana.yaml
apiVersion: toolhive.stacklok.dev/v1beta1
kind: MCPServer
metadata:
  name: grafana
  namespace: platform-tools
spec:
  image: grafana/mcp-grafana:latest
  transport: streamable-http
  mcpPort: 8000
  proxyPort: 8080
  env:
    - name: GRAFANA_URL
      value: "https://your-grafana.internal"
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
```

Once running, agents can query: dashboards, Prometheus instant/range queries, Loki logs, alert rule state, OnCall on-call schedules, and Grafana Incident. Source: [grafana/mcp-grafana](https://github.com/grafana/mcp-grafana).

## MCPServer: GitHub MCP

```yaml
# mcp-servers/github.yaml
apiVersion: toolhive.stacklok.dev/v1beta1
kind: MCPServer
metadata:
  name: github
  namespace: platform-tools
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
```

```bash
kubectl -n platform-tools create secret generic github-token \
  --from-literal=token=<GITHUB_PAT>
```

## MCPServer: Kubernetes MCP

```yaml
# mcp-servers/kubernetes.yaml
apiVersion: toolhive.stacklok.dev/v1beta1
kind: MCPServer
metadata:
  name: kubernetes
  namespace: platform-tools
spec:
  image: ghcr.io/manusa/kubernetes-mcp-server:latest
  transport: streamable-http
  mcpPort: 8080
  proxyPort: 8080
  resources:
    limits:
      cpu: '200m'
      memory: '256Mi'
    requests:
      cpu: '50m'
      memory: '128Mi'
```

Note: The Kubernetes MCP server uses the pod's service account to query the cluster. The operator auto-creates a ServiceAccount — bind it to the RBAC permissions your MCP server needs.

## MCPRemoteProxy: External SaaS tools

```yaml
# mcp-servers/linear-proxy.yaml
apiVersion: toolhive.stacklok.dev/v1beta1
kind: MCPRemoteProxy
metadata:
  name: linear
  namespace: platform-tools
spec:
  url: https://mcp.linear.app/mcp
  proxyPort: 8080
```

The operator creates a proxy pod that applies auth, rate limiting, and audit logging to the external endpoint — same operational model as in-cluster servers.

## VirtualMCPServer: One endpoint, all backends

```yaml
# virtual-mcp.yaml
apiVersion: toolhive.stacklok.dev/v1beta1
kind: VirtualMCPServer
metadata:
  name: platform-tools-vmcp
  namespace: platform-tools
spec:
  backends:
    - name: grafana
      namespace: platform-tools
    - name: github
      namespace: platform-tools
    - name: kubernetes
      namespace: platform-tools
    - name: linear
      namespace: platform-tools
  proxyPort: 9090
```

Agents connect once and can query Grafana dashboards, search GitHub issues, inspect cluster state, and update Linear tickets — all through one endpoint with centralised OIDC auth.

Agent clients connect to the VirtualMCPServer endpoint and get access to all tools from all backends. OIDC auth configured on the vMCP applies to all backends centrally.

## Horizontal scaling with Redis

For production deployments with multiple proxy replicas:

```yaml
spec:
  replicas: 2
  backendReplicas: 2
  sessionStorage:
    provider: redis
    address: redis.platform-tools.svc.cluster.local:6379
    db: 0
    keyPrefix: toolhive-sessions
    passwordRef:
      name: redis-password
      key: password
```

## ArgoCD Application

```yaml
# argocd/toolhive-fleet.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: toolhive-mcp-fleet
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/platform-config
    targetRevision: main
    path: mcp-servers/
  destination:
    server: https://kubernetes.default.svc
    namespace: platform-tools
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

## Check fleet status

```bash
# All ToolHive resources in the namespace
kubectl get toolhive -n platform-tools

# MCPServer status
kubectl get mcpservers -n platform-tools

# Describe a specific server
kubectl describe mcpserver github -n platform-tools

# Operator logs
kubectl logs -n toolhive-system -l app.kubernetes.io/name=toolhive-operator --tail=50
```

## Inputs

- Kubernetes cluster with Helm access
- GitHub PAT stored as Kubernetes secret (or ESO ExternalSecret)
- `values.yaml` for namespace mode if multi-tenant
- ArgoCD Application pointing at your MCPServer manifests directory

## Outputs

- `platform-tools` namespace running GitHub, Kubernetes, OSV MCP servers
- VirtualMCPServer at `http://mcp-platform-tools-vmcp-proxy.platform-tools:9090/mcp`
- Auto-provisioned RBAC per server (ServiceAccount, Role, RoleBinding)
- Audit logs via operator + proxy containers
