# AGENTS.md

<!-- zone:1:start -->

## Sync model

This file is zone-structured and managed by the platform-standards sync engine.

- **Zone 1** (this section) is locked. Changes must go through a PR to `platform-standards`.
- **Zone 2** is guarded. Teams may propose changes; platform review required.
- **Zone 3** is free. Teams own this section entirely.

Template version: 1.0.0

## Forbidden paths

Do not modify, delete, or move files in the following paths without explicit approval:

- `infra/` — managed by Crossplane compositions
- `crds/` — managed by the cluster upgrade pipeline
- `.github/workflows/` — CI/CD pipelines; changes require platform team review
- `Makefile` targets prefixed with `platform-` — shared tooling targets

Do not rename ArgoCD Application resources. Names follow `<team>-<service>-<env>` and downstream tooling (Grafana dashboards, Notification controller, scripts) depends on them.

## Naming conventions

| Resource | Pattern | Example |
|---|---|---|
| ArgoCD Application | `<team>-<service>-<env>` | `payments-api-prod` |
| Namespace | `<team>-<env>` | `payments-prod` |
| ConfigMap/Secret | `<service>-<purpose>` | `api-db-credentials` |
| Helm release | `<service>` | `api` |

Deviating from these patterns breaks downstream tooling silently. If a service name must change, coordinate with the platform team to update the Notification controller and dashboards first.

## Running tests

Before opening a PR, run the full validation suite:

```bash
make validate
```

This runs linting, schema validation, and a dry-run ArgoCD diff. Individual checks:

```bash
make lint          # YAML lint + kustomize build check
make schema-check  # validate manifests against CRD schemas
make argocd-diff   # show what ArgoCD would apply
```

<!-- zone:1:end -->

<!-- zone:2:start -->

## Team conventions

> This section is guarded. Teams may edit it, but platform review is required on PRs that change Zone 2 content.

Document team-specific conventions that extend (not override) Zone 1 here.
Examples: preferred Helm values patterns, team-specific secret naming, monitoring label conventions.

<!-- zone:2:end -->

<!-- zone:3:start -->

## Repo-specific notes

> This section is free. Teams own it entirely.

Add anything useful for AI coding agents working in this repo — context about the domain, gotchas, preferred libraries, links to runbooks, etc.

<!-- zone:3:end -->
