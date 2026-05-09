# Example: AI Incident Triage

**Goal:** Automatically gather incident context and post a structured triage summary to Slack within 90 seconds of an alert firing.

Related blog post: [AI Incident Triage: Faster Summaries, Safer Actions](/blog/2026/04/09/ai-incident-triage-faster-summaries-safer-actions/)

## Problem

Context gathering is the slowest part of every incident. Before an engineer can make a decision, they need to: pull the right logs, check the error rate dashboard, read recent deploy notifications, and find whether this has happened before. This takes 10–20 minutes. AI can do it in 90 seconds.

## Workflow

1. **Alert fires**: PagerDuty triggers a webhook to GitHub Actions
2. **Gather** (parallel): recent deploys, error rate, affected services, recent commits, relevant runbooks
3. **Summarise**: AI produces a structured summary — blast radius, key facts, hypotheses, proposed actions
4. **Post**: summary posted to the incident Slack channel with interactive action buttons
5. **Approve**: engineer clicks a button to run a safe remediation step, or copies the command for manual execution
6. **Log**: all actions (run or dismissed) are logged with the engineer's identity

## Triage summary format

The summary follows a fixed structure optimised for reading at 3am:

```
## Incident Summary

**Status:** Active / Degraded / Unknown
**Blast radius:** Which services/users and estimated scope
**Started approximately:** Time estimate from error rate data

## What we know
- [3-5 factual bullet points]

## Most likely causes
- [2-3 ranked hypotheses with evidence]

## Proposed actions
- [Action name] — [what it does] — `kubectl command` — Risk: Low/Medium/High

## What to check next
- [2-3 diagnostic steps]
```

## Action gates

- **Low-risk actions**: appear as Slack buttons — single click to run
- **Medium-risk actions**: appear as buttons with a confirmation dialog
- **High-risk actions**: appear as text only — engineer must copy-paste and run manually

## Scripts

```bash
# Test the triage pipeline with a sample alert
python scripts/incident/test-triage.py --alert-file examples/sample-alert.json

# Simulate the full loop (gather + summarise + post)
ANTHROPIC_API_KEY=<key> SLACK_BOT_TOKEN=<token> python scripts/incident/full-triage.py
```

## Environment variables required

```bash
ANTHROPIC_API_KEY=<key>
PAGERDUTY_TOKEN=<token>
GITHUB_TOKEN=<token>
GITHUB_REPO=org/repo
DATADOG_API_KEY=<key>    # or PROMETHEUS_URL=<url>
SLACK_BOT_TOKEN=<token>
INCIDENT_CHANNEL=#incidents
```

## Agent prompts

- **Context Gatherer**: query PagerDuty, GitHub, Prometheus/Datadog in parallel; produce structured JSON context
- **Triage Analyst**: read context, produce fixed-format summary under 300 words
- **Action Proposer**: for each remediation option, classify risk level and provide exact command

## What this is not

This does not replace incident commanders. It does not diagnose novel failures with no prior pattern. It handles the first 15 minutes so engineers arrive with context, not a blank page.
