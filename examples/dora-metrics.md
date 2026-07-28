# Example: DORA Metrics Collection

**Goal:** Automatically collect all four DORA metrics weekly from GitHub, PagerDuty, and deployment data, and post a trend summary to Slack.

Related blog post: [DevEx Metrics That Matter (and How to Automate Them)](/blog/2026/04/07/devex-metrics-that-matter-and-how-to-automate-them/)

## The four metrics

| Metric | What it measures | Source |
|--------|-----------------|--------|
| **Lead time** | First commit to production deployment | GitHub Commits + Deployments |
| **Deployment frequency** | Deployments per week to production | GitHub Deployments |
| **Change failure rate** | % of deployments causing an incident | GitHub Deployments + PagerDuty |
| **MTTR** | Time from incident creation to resolution | PagerDuty |

## DORA performance bands

| Metric | Elite | High | Medium | Low |
|--------|-------|------|--------|-----|
| Lead time | < 1 day | < 1 week | 1–4 weeks | > 1 month |
| Deployment freq | Multiple/day | 1/day | Weekly | Monthly |
| Change failure rate | < 5% | 5–10% | 10–15% | > 15% |
| MTTR | < 1 hour | < 1 day | < 1 week | > 1 week |

## Scripts

```bash
# Collect all four metrics for the last 30 days
python scripts/metrics/collect-dora.py --days 30

# Output: /tmp/dora-metrics.json
```

```python
# Sample output structure
{
  "period": {"start": "2026-03-12", "end": "2026-04-12"},
  "lead_time": {
    "avg_hours": 18.4,
    "p95_hours": 42.1,
    "sample_count": 23
  },
  "deployment_frequency": {
    "per_week": 3.2,
    "total": 13
  },
  "change_failure_rate": {
    "rate_pct": 7.7,
    "failures": 1,
    "deployments": 13
  },
  "mttr": {
    "avg_minutes": 34,
    "median_minutes": 22,
    "sample_count": 8
  }
}
```

## Environment variables required

```bash
GITHUB_TOKEN=<token>
GITHUB_REPO=org/repo
PAGERDUTY_TOKEN=<token>
SLACK_WEBHOOK=<platform-channel-webhook>
```

## Weekly schedule

Run every Monday morning to cover the previous week:

```yaml
# GitHub Actions schedule
on:
  schedule:
    - cron: '0 9 * * MON'
```

## Agent prompts

- **Collector**: query GitHub and PagerDuty APIs; produce structured JSON with all four metrics
- **Analyst**: compare current week to previous week and previous month; identify meaningful changes (>10%)
- **Reporter**: write a concise 200-word Slack summary with trend arrows (↑ ↓ →) and one action item

## Using the data

Metrics are only useful when they drive conversations:

- **High lead time**: where in the pipeline are changes waiting? PRs? Staging? Approvals?
- **Low deployment frequency**: are changes being batched unnecessarily?
- **High change failure rate**: are tests catching the right things? Are rollbacks fast?
- **High MTTR**: does on-call have the context they need when an alert fires?

Post weekly. Review in the platform retrospective. Set a quarterly target for one metric to improve.
