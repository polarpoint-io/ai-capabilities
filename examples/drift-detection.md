# Example: GitOps Drift Detection

**Goal:** Detect live cluster drift from Git state, classify it, and open targeted fix PRs.

Related blog post: [GitOps + AI Drift Detection](/blog/2026/04/07/gitops-ai-drift-detection-catch-it-before-prod/)

## Problem

ArgoCD `OutOfSync` is not enough. It tells you drift exists but not whether it is harmless (controller-managed fields) or risky (manual edits to spec). Without classification, engineers ignore all drift alerts.

## Workflow

1. **Detect**: query ArgoCD for all OutOfSync Applications
2. **Diff**: run `kubectl diff` against each Application to get the actual divergence
3. **Classify**: feed the diff to an AI classifier — HARMLESS / NEEDS_REVIEW / RISKY
4. **Act**: open a targeted PR per RISKY/NEEDS_REVIEW resource; skip HARMLESS
5. **Notify**: post a Slack summary of the detection run

## Inputs

- ArgoCD API (OutOfSync Applications)
- kubectl diff output (live vs desired state)
- Git repository (for PR creation)

## Outputs

- GitHub PRs: one per drifted resource requiring attention
- Slack summary: classification breakdown + PR links
- Audit log: all detections and classifications

## Classification rules

| Verdict | Examples |
|---------|---------|
| **HARMLESS** | `status.*` fields, `resourceVersion`, `uid`, injected sidecars, admission annotations |
| **NEEDS_REVIEW** | Helm-generated value changes, config that could be intentional drift |
| **RISKY** | Manual edits to `spec.*`, changed resource limits, replicas, security context |

## Scripts

```bash
# Detect drift and open PRs
bash scripts/detect-drift.sh

# Classify a specific diff file
python scripts/classify-drift.py <app-name> /tmp/drift-<app>.diff

# Run the full loop (detect + classify + PR)
python scripts/drift-detection-loop.py
```

## Environment variables required

```bash
ARGOCD_SERVER=argocd.your-cluster.example.com
ARGOCD_AUTH_TOKEN=<token>
GITHUB_TOKEN=<token>
GITHUB_REPO=org/repo
ANTHROPIC_API_KEY=<key>
SLACK_WEBHOOK=<webhook-url>
```

## Agent prompts

- **Detector**: query ArgoCD API, produce diff files per Application
- **Classifier**: categorise each diff resource — HARMLESS / NEEDS_REVIEW / RISKY with reason
- **PR Author**: open targeted PRs for actionable drift with full context
- **Reporter**: post Slack summary with verdict breakdown and PR links

## Schedule

Run every 30 minutes in non-prod, every 15 in prod. Run on-demand before and after major deployments.
