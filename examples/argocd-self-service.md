# Example: Self-Service GitOps with ArgoCD

**Goal:** Let developers onboard new services without platform tickets — a catalogue entry triggers ApplicationSet deployment with Kyverno policy guardrails enforced automatically.

Related blog post: [GitOps as a Product: Building Self-Service with ArgoCD](/blog/2026/03/02/gitops-as-a-product-building-self-service-with-argo-cd/)

## Problem

Every new service requires a platform ticket, custom YAML, and a queue. Platform engineers manually verify resource limits, labels, and namespace configuration on every onboarding. This doesn't scale and creates toil that blocks everyone.

## Workflow

1. **Developer** adds a service definition YAML under `teams/<team>/services/`
2. **PR review**: team lead approves the service definition
3. **Merge**: ApplicationSet detects the new file and creates ArgoCD Applications automatically
4. **Kyverno validation**: resource limits, required labels, registry restrictions enforced at admission
5. **Deploy**: service is live in the target namespaces — no platform team involvement

## Repository layout

```
platform-config/
├── teams/
│   ├── payments/
│   │   └── services/
│   │       ├── payments-api.yaml    ← developer adds this
│   │       └── payments-worker.yaml
│   └── identity/
│       └── services/
│           └── auth-service.yaml
├── templates/
│   ├── api-service/             ← Helm chart for API services
│   ├── worker-service/          ← Helm chart for background workers
│   └── scheduled-job/           ← Helm chart for cron jobs
└── policies/
    └── kyverno/
        ├── require-resource-limits.yaml
        ├── require-team-labels.yaml
        └── restrict-image-registries.yaml
```

## Service definition (developer creates this)

```yaml
# teams/payments/services/payments-api.yaml
service:
  name: payments-api
  type: api-service          # maps to templates/api-service/
  image: registry.example.com/payments/api
  tag: "1.4.2"
  replicas: 2
  resourceTier: standard     # small / standard / large (maps to preset limits)

environments:
  - name: dev
    cluster: dev-uk
  - name: staging
    cluster: staging-uk
  - name: production
    cluster: prod-uk

team:
  name: payments
  costCentre: CC-0042
  slackChannel: "#payments-platform"
```

## ApplicationSet

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: team-services
  namespace: argocd
spec:
  generators:
    - matrix:
        generators:
          - git:
              repoURL: https://github.com/your-org/platform-config
              revision: HEAD
              files:
                - path: "teams/*/services/*.yaml"
          - list:
              elements:
                - environment: dev
                - environment: staging
                - environment: production
  template:
    metadata:
      name: '{{service.name}}-{{environment}}'
    spec:
      project: '{{team.name}}'
      source:
        repoURL: https://github.com/your-org/platform-config
        targetRevision: HEAD
        path: 'templates/{{service.type}}'
        helm:
          values: |
            service:
              name: {{service.name}}
              image: {{service.image}}:{{service.tag}}
              replicas: {{service.replicas}}
            resources:
              tier: {{service.resourceTier}}
            team:
              name: {{team.name}}
              costCentre: {{team.costCentre}}
            environment: {{environment}}
      destination:
        server: '{{clusters[environment].server}}'
        namespace: '{{team.name}}-{{environment}}'
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
          - CreateNamespace=true
```

## Scripts

```bash
# Validate a new service definition before opening a PR
python scripts/gitops/validate-service.py \
  --file teams/payments/services/payments-api.yaml

# Generate service definition interactively
python scripts/gitops/new-service.py \
  --team payments \
  --type api-service \
  --output teams/payments/services/

# Check service status across all environments
argocd app list --selector service.name=payments-api
```

## Environment variables required

```bash
ARGOCD_SERVER=argocd.your-cluster.example.com
ARGOCD_AUTH_TOKEN=<token>
GITHUB_TOKEN=<token>
GITHUB_REPO=org/platform-config
```

## Inputs

- Service definition YAML (developer-created, reviewed via PR)
- ApplicationSet templates in `templates/`
- Kyverno ClusterPolicies in `policies/kyverno/`

## Outputs

- ArgoCD Applications per service × environment combination
- Kyverno admission reports (policy compliance visible in ArgoCD)
- Namespaces auto-created with team labels and resource quotas

## Resource tiers

| Tier | CPU request | CPU limit | Memory request | Memory limit |
|------|------------|-----------|----------------|--------------|
| small | 50m | 200m | 64Mi | 256Mi |
| standard | 100m | 500m | 128Mi | 512Mi |
| large | 250m | 1000m | 256Mi | 1Gi |

Developers pick a tier, not raw values. Platform team controls what the tiers mean.
