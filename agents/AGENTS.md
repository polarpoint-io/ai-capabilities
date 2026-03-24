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
