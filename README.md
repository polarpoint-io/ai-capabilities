# AI Capabilities

Companion repository for the **AGENTS.md for Platform Engineering** blog post.

This repo contains:
- Example `AGENTS.md` patterns for platform workflows
- Sample scripts to collect metrics and generate outputs
- Walkthrough examples you can run locally

## Structure

```
/agents
  AGENTS.md
/examples
  platform-release-checklist.md
  incident-runbook.md
  infra-bootstrap.md
  slo-review.md
  sprint-review-deck.md
/scripts
  setup-linux.sh
  setup-macos.sh
  metrics/sample-data.json
  metrics/summarise-metrics.py
  marp/generate-deck.sh
/.github/workflows
  lint.yml
  test.yml
```

## Quick Start

1) **Bring up Tailscale + OpenClaw**

```bash
# Linux
./scripts/setup-linux.sh

# macOS
./scripts/setup-macos.sh
```

2) Read `/agents/AGENTS.md`
3) Pick an example from `/examples`
4) Run the scripts in `/scripts`

> Tip: set `TAILSCALE_AUTHKEY` to avoid interactive login.

## License

Apache-2.0
