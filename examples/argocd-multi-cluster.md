# Example: Multi-Cluster GitOps with ArgoCD

**Goal:** Manage a fleet of Kubernetes clusters from a single ArgoCD control plane using a cluster registry and ApplicationSets — no per-cluster manual configuration.

Related blog post: [Multi-Cluster GitOps with ArgoCD: The Operational Blueprint](/blog/2026/03/02/multi-cluster-gitops-with-argo-cd-the-operational-blueprint/)

## Problem

Every new cluster requires copying configuration from an existing one, tweaking by hand, and hoping nothing was missed. Six months in you have seven clusters and no real confidence they're running the same thing. Config drift is an architectural problem, not a discipline problem.

## Workflow

1. **Register**: add a cluster secret to the `argocd` namespace with labels for environment, region, tier
2. **Fan out**: ApplicationSets match against labels and deploy automatically to matching clusters
3. **Promote**: update values in the target cluster directory via PR — ArgoCD syncs
4. **Verify**: ArgoCD self-heal catches any live divergence from Git state

## Repository layout

```
platform-config/
├── clusters/
│   ├── dev-uk/
│   │   └── values.yaml
│   ├── staging-uk/
│   │   └── values.yaml
│   ├── prod-uk/
│   │   └── values.yaml
│   └── prod-eu/
│       └── values.yaml
├── templates/
│   ├── platform-baseline/    ← Helm chart applied to every cluster
│   └── observability/        ← per-environment observability stack
└── applicationsets/
    ├── platform-baseline.yaml
    └── observability.yaml
```

## Cluster registry secret

```yaml
# kubectl apply -n argocd -f cluster-prod-uk.yaml
apiVersion: v1
kind: Secret
metadata:
  name: prod-uk-cluster
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: cluster
    environment: production
    region: uk
    tier: critical
type: Opaque
stringData:
  name: prod-uk
  server: https://prod-uk.k8s.example.com
  config: |
    {
      "bearerToken": "<token>",
      "tlsClientConfig": {
        "insecure": false,
        "caData": "<base64-encoded-ca>"
      }
    }
```

## ApplicationSet — production fleet

```yaml
# applicationsets/platform-baseline.yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: platform-baseline
  namespace: argocd
spec:
  generators:
    - clusters:
        selector:
          matchLabels:
            environment: production
  template:
    metadata:
      name: '{{name}}-platform-baseline'
    spec:
      project: platform
      source:
        repoURL: https://github.com/your-org/platform-config
        targetRevision: HEAD
        path: 'clusters/{{name}}'
        helm:
          valueFiles:
            - values.yaml
      destination:
        server: '{{server}}'
        namespace: platform-system
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
          - CreateNamespace=true
```

## Scripts

```bash
# Register a new cluster
bash scripts/gitops/register-cluster.sh \
  --name prod-eu \
  --server https://prod-eu.k8s.example.com \
  --environment production \
  --region eu \
  --tier critical \
  --token <bearer-token> \
  --ca-file /path/to/ca.crt

# List all registered clusters with labels
kubectl get secrets -n argocd -l argocd.argoproj.io/secret-type=cluster \
  -o custom-columns=NAME:.metadata.name,ENV:.metadata.labels.environment,REGION:.metadata.labels.region

# Check ApplicationSet sync status across fleet
argocd appset list
argocd app list --selector environment=production
```

## Environment variables required

```bash
ARGOCD_SERVER=argocd.your-cluster.example.com
ARGOCD_AUTH_TOKEN=<token>
GITHUB_TOKEN=<token>        # for PR-based promotion
GITHUB_REPO=org/platform-config
```

## Inputs

- Cluster kubeconfig / bearer token + CA cert
- `clusters/<name>/values.yaml` — per-cluster configuration overrides
- ApplicationSet templates in `applicationsets/`

## Outputs

- ArgoCD Applications automatically created per matching cluster
- Drift detection via ArgoCD's self-heal (alerts on any live divergence)

## Adding a new cluster (end-to-end)

1. Obtain kubeconfig credentials for the new cluster
2. Run `register-cluster.sh` to create the ArgoCD secret
3. Create `clusters/<new-cluster-name>/values.yaml` in Git via PR
4. Merge the PR — ApplicationSets targeting matching labels deploy automatically
5. Verify with `argocd app list --selector environment=<env>`

New cluster goes from registered to fully configured without touching any Application resource directly.
