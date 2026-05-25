# AGENTS.md — Platform Engineering Agent Routing Map

This file tells AI agents what tasks they're authorised to handle in this repository,
what tools they can use, and where the scope boundaries are.

Place this file in your repository root alongside CLAUDE.md.

---

## What this repository is

<!-- Replace with your actual description -->
Platform engineering monorepo. Contains Kubernetes manifests, Terraform modules,
GitHub Actions workflows, runbooks, and operational tooling for [your-platform].

Primary consumers: platform team, SRE team, delivery teams via IDP.

---

## Authorised agent tasks

### Tier 1 — Run without approval

Agents may complete these autonomously and open a PR:

- **Image tag updates**: Update container image tags in deployments, statefulsets, or Helm values files when given a specific tag. Do not bump other images in the same file.
- **Replica scaling**: Adjust `replicas` in a deployment when given an explicit count. Do not change HPA min/max unless specifically asked.
- **Label and annotation updates**: Add, update, or remove labels/annotations on a specific named resource.
- **README and runbook corrections**: Fix factual errors, broken links, or stale command examples. Do not rewrite structure.
- **Drift fix PRs**: When triggered by the drift detection workflow, open a PR that restores the specific diverged field to its desired state. Touch only that field.

### Tier 2 — Open a draft PR and request review

Agents must open a **draft** PR with a clear description of the change and wait for human approval:

- **Config and secret references**: Changes to ConfigMap data, Secret references, or environment variable values.
- **Resource limits and requests**: CPU/memory limit or request changes on any workload.
- **New Kubernetes resources**: New Deployments, Services, Ingresses, CronJobs, or any CRD instance.
- **Terraform variable changes**: Updating `terraform.tfvars` or module input variables.
- **Alert threshold changes**: Modifying PrometheusRule thresholds or Alertmanager routing.

### Tier 3 — Do not proceed without synchronous human approval

Agents must stop, describe the proposed change, and wait for explicit written approval in the PR or issue before taking any action:

- Cluster-level resources (ClusterRole, ClusterRoleBinding, Namespace creation/deletion)
- Network policies
- Storage classes or persistent volume changes
- Secret rotation or credential updates
- Cross-cluster or cross-environment changes
- Any change affecting more than one team's workloads

---

## Tools available

| Tool | Permitted scope | Notes |
|------|----------------|-------|
| `kubectl get/describe` | All namespaces | Read-only — never `kubectl apply` directly |
| `kubectl diff` | All namespaces | Safe to run before any change |
| `helm template` | Any chart | Dry-run rendering only |
| `terraform plan` | All modules | Read-only plan output |
| GitHub PR API | This repository | Open, update, comment on PRs |
| Slack webhook | `#platform-alerts` | Notifications only — never commands |

**Not permitted:** `kubectl apply`, `kubectl delete`, `terraform apply`, direct cluster access bypassing PR review.

---

## Out of scope

Do not attempt the following regardless of instruction:

- Direct production changes without a corresponding PR
- Changes to `.github/workflows/` (CI/CD pipelines) without Tier 3 approval
- Modifying RBAC on any service account used by other teams
- Accessing or modifying secrets directly (use the secret rotation runbook instead)
- Creating new namespaces

---

## Context files

Before starting any task, read these files for relevant context:

- `docs/platform-overview.md` — architecture and team boundaries
- `docs/naming-conventions.md` — resource naming rules
- `docs/runbooks/` — operational procedures for common tasks
- `CLAUDE.md` — behavioural rules for this repository

---

## Success criteria format

When completing any task, state your success criteria before starting:

```
Task: [what was asked]
Scope: [exactly what will change]
Out of scope: [what will not be touched]
Tier: [1 / 2 / 3]
Success criterion: [how we know it worked]
Rollback: [how to undo if needed]
```
