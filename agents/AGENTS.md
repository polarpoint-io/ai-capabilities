# AGENTS.md

## Mission
Deliver platform work predictably and safely using repeatable workflows.

## Workflow
1. Plan — scope, success criteria, risks
2. Survey — current state + gaps
3. Ideate — options + tradeoffs
4. Review — approve approach + gates
5. Build — implement + automate
6. Document — runbooks + diagrams
7. Validate — operational review
8. Ship — release readiness

## Quality Gates
- Every change has a named owner
- Risks documented before build
- Docs updated before release
- Rollback plan included

## Standards
- Naming: <team>-<service>-<env>
- Environments: dev → staging → prod
- Tooling: Helm + ArgoCD
- Metrics: latency p95, error rate, request volume

## Outputs
- Plan: `/examples/*.md`
- Scripts: `/scripts/*`
- Metrics: `/scripts/metrics/*`

## Available examples

| Example | Goal |
|---------|------|
| `platform-release-checklist.md` | Safe, gate-based release workflow |
| `incident-runbook.md` | Standardised incident response |
| `incident-triage.md` | AI-assisted context gathering for incidents |
| `infra-bootstrap.md` | New environment bootstrap |
| `slo-review.md` | Monthly SLO review with action items |
| `sprint-review-deck.md` | Marp deck from metrics |
| `drift-detection.md` | GitOps drift classification + fix PRs |
| `cost-monitoring.md` | Cloud cost anomaly detection + fix PRs |
| `policy-gate.md` | OPA/Kyverno validation for agent changes |
| `dora-metrics.md` | DORA metrics collection and reporting |

## Key scripts

- `scripts/metrics/collect-dora.py` — all four DORA metrics from GitHub + PagerDuty
- `scripts/detect-drift.sh` — query ArgoCD for OutOfSync Applications
- `scripts/classify-drift.py` — AI classification of kubectl diff output
