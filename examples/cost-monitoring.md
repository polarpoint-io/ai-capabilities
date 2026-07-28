# Example: AI FinOps Cost Monitoring

**Goal:** Detect cloud cost anomalies daily and open targeted fix PRs with estimated savings.

Related blog post: [AI for FinOps: Cost Drift Detection and Fix PRs](/blog/2026/04/10/ai-for-finops-cost-drift-detection-and-fix-prs/)

## Problem

Budget alerts fire too late (usually after 30%+ overspend has accumulated). Manual cost reviews happen monthly. Between detection and fix, costs compound. The right fix requires context — which service, what changed, what the specific configuration adjustment is.

## Workflow

1. **Query**: pull daily costs from AWS Cost Explorer (or Azure Cost Management) grouped by service tag
2. **Baseline**: compare each service's cost to the rolling 14-day average
3. **Flag**: identify services more than 2 standard deviations above baseline
4. **Analyse**: for each anomaly, query cluster context (autoscaler config, pod counts, recent deploys)
5. **Fix**: AI proposes a specific config or code change with estimated monthly saving
6. **PR**: open a draft or ready PR depending on confidence level

## Inputs

- AWS Cost Explorer API (daily costs by service tag)
- Kubernetes API (pod counts, HPA config, resource limits)
- GitHub Deployments (recent changes per service)
- 14-day cost history (rolling baseline)

## Outputs

- GitHub PRs: one per anomaly — targeted fix with cost impact estimate
- GitHub Issues: low-confidence anomalies that need human investigation
- Slack daily summary: anomaly count, total excess cost, PR links

## Required tagging

Cost monitoring only works with consistent resource tagging. Every cloud resource needs:

```
service: <service-name>
team: <team-name>
environment: prod | staging | dev
```

Without these tags, costs are unattributable and the anomaly detection is blind.

## Confidence levels and PR types

| Confidence | Action |
|------------|--------|
| **High** | Open ready-to-review PR |
| **Medium** | Open draft PR for human refinement |
| **Low** | Open GitHub Issue for human investigation |

## Scripts

```bash
# Query costs for the last 14 days
python scripts/finops/query-costs.py --days 14

# Detect anomalies against baseline
python scripts/finops/detect-anomalies.py

# Propose fixes for flagged anomalies
ANTHROPIC_API_KEY=<key> python scripts/finops/propose-fixes.py

# Open PRs for high/medium confidence fixes
GITHUB_TOKEN=<token> python scripts/finops/open-fix-prs.py
```

## Environment variables required

```bash
AWS_ACCESS_KEY_ID=<cost-reader-key>
AWS_SECRET_ACCESS_KEY=<cost-reader-secret>
ANTHROPIC_API_KEY=<key>
GITHUB_TOKEN=<token>
GITHUB_REPO=org/repo
SLACK_WEBHOOK=<finops-channel-webhook>
KUBECONFIG=<path-or-base64>
```

## Agent prompts

- **Analyst**: compare service costs to baseline; flag anomalies with z-score
- **Investigator**: query cluster context for flagged service; identify likely cause
- **Fixer**: propose specific config change with estimated monthly saving
- **PR Author**: open fix PR with anomaly details, proposed change, and verification steps
