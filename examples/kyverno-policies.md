# Example: GitOps Policy-as-Code with Kyverno

**Goal:** Enforce platform standards at admission — resource limits, required labels, approved registries — via Kyverno ClusterPolicies that live in Git and sync via ArgoCD.

Related blog post: [GitOps Policy-as-Code with Argo CD + Kyverno](/blog/2026/04/07/gitops-policy-as-code-with-argo-cd-kyverno/)

## Problem

ArgoCD syncs whatever is in Git without checking whether it's correct. A deployment missing resource limits, exposing a service publicly, or using an untrusted image syncs cleanly. Kyverno adds the correctness layer — policies are Kubernetes resources that live in Git like everything else.

## Workflow

1. **Install**: deploy Kyverno as a webhook via Helm
2. **Audit first**: apply all policies in `Audit` mode — violations logged, nothing blocked
3. **Remediate**: fix existing non-compliant workloads surfaced in policy reports
4. **Enforce**: switch to `Enforce` mode — violations blocked at admission
5. **Iterate**: new policies always start in Audit, graduate to Enforce via PR

## Install Kyverno

```bash
helm repo add kyverno https://kyverno.github.io/kyverno/
helm install kyverno kyverno/kyverno \
  -n kyverno \
  --create-namespace \
  --set replicaCount=3   # HA for production

# Verify webhook is registered
kubectl get validatingwebhookconfiguration | grep kyverno
```

## Core policies (apply via ArgoCD from `policies/kyverno/`)

### Require resource limits

```yaml
# policies/kyverno/require-resource-limits.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-resource-limits
  annotations:
    policies.kyverno.io/title: Require Resource Limits
    policies.kyverno.io/severity: high
spec:
  validationFailureAction: Enforce
  background: true
  rules:
    - name: check-container-limits
      match:
        any:
          - resources:
              kinds: [Pod]
      validate:
        message: "All containers must define CPU and memory limits."
        pattern:
          spec:
            containers:
              - resources:
                  limits:
                    cpu: "?*"
                    memory: "?*"
```

### Require team labels

```yaml
# policies/kyverno/require-team-labels.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-team-labels
  annotations:
    policies.kyverno.io/title: Require Team Labels
    policies.kyverno.io/severity: medium
spec:
  validationFailureAction: Enforce
  rules:
    - name: check-team-labels
      match:
        any:
          - resources:
              kinds: [Deployment, StatefulSet, DaemonSet]
      validate:
        message: "Workloads must have 'team', 'environment', and 'cost-centre' labels."
        pattern:
          metadata:
            labels:
              team: "?*"
              environment: "?*"
              cost-centre: "?*"
```

### Restrict image registries

```yaml
# policies/kyverno/restrict-image-registries.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: restrict-image-registries
  annotations:
    policies.kyverno.io/title: Restrict Image Registries
    policies.kyverno.io/severity: high
spec:
  validationFailureAction: Enforce
  rules:
    - name: check-registry
      match:
        any:
          - resources:
              kinds: [Pod]
      validate:
        message: "Images must come from registry.example.com or approved public registries."
        pattern:
          spec:
            containers:
              - image: "registry.example.com/* | gcr.io/distroless/* | public.ecr.aws/*"
```

### Block latest tag in production

```yaml
# policies/kyverno/no-latest-tag-production.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: no-latest-tag-production
spec:
  validationFailureAction: Enforce
  rules:
    - name: check-image-tag
      match:
        any:
          - resources:
              kinds: [Pod]
              namespaceSelector:
                matchLabels:
                  environment: production
      validate:
        message: "Image tag 'latest' is not permitted in production namespaces."
        pattern:
          spec:
            containers:
              - image: "!*:latest"
```

### Auto-generate namespace guardrails (Generate policy)

```yaml
# policies/kyverno/generate-namespace-defaults.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: generate-namespace-defaults
spec:
  rules:
    - name: generate-resource-quota
      match:
        any:
          - resources:
              kinds: [Namespace]
              selector:
                matchExpressions:
                  - key: team
                    operator: Exists
      generate:
        apiVersion: v1
        kind: ResourceQuota
        name: team-quota
        namespace: "{{request.object.metadata.name}}"
        data:
          spec:
            hard:
              requests.cpu: "4"
              requests.memory: "8Gi"
              limits.cpu: "8"
              limits.memory: "16Gi"
              pods: "50"
```

## Scripts

```bash
# Apply all policies in Audit mode first
kubectl apply -f policies/kyverno/ --dry-run=server

# Check policy reports — see what would fail before enforcing
kubectl get policyreport -A
kubectl get clusterpolicyreport

# Summarise violations across the cluster
python scripts/kyverno/summarise-violations.py

# Switch a specific policy from Audit to Enforce
kubectl patch clusterpolicy require-resource-limits \
  --type merge \
  -p '{"spec":{"validationFailureAction":"Enforce"}}'
```

## Environment variables required

No external credentials needed — Kyverno operates as a Kubernetes admission webhook using in-cluster service account permissions.

## Inputs

- Kyverno ClusterPolicy YAML files (live in Git, synced via ArgoCD)
- Kubernetes resources submitted to the cluster (evaluated by Kyverno at admission)

## Outputs

- **PolicyReport**: per-namespace report of policy violations for existing resources
- **ClusterPolicyReport**: cluster-wide report
- **Admission response**: ALLOW or DENY with a clear policy violation message

## Recommended rollout order

| Phase | Action |
|-------|--------|
| Week 1 | Install Kyverno, apply all policies in Audit mode |
| Week 2 | Review PolicyReports, fix existing violations in dev/staging |
| Week 3 | Enforce resource limits and team labels in dev/staging |
| Week 4 | Clear production violations, enforce in production |
| Ongoing | New policies always start Audit → Enforce after one sprint |
