# AGENTS.md drift detector

Scans a GitHub org (or a list of repos) and reports which ones have Zone 1 content that has drifted from the `platform-standards` template.

## Requirements

Python 3.9+, no external dependencies (stdlib only).

## Usage

```bash
# Scan all repos in an org
python detect-drift.py \
  --org your-org \
  --token $GITHUB_TOKEN \
  --schema https://raw.githubusercontent.com/your-org/platform-standards/main/schema.json

# Scan specific repos
python detect-drift.py \
  --org your-org \
  --repos api,frontend,platform-infra \
  --token $GITHUB_TOKEN \
  --schema ./schema.json

# JSON output for dashboards / Slack webhooks
python detect-drift.py ... --output json

# Exit 1 if any repo is drifted or missing (useful in CI)
python detect-drift.py ... --fail-on-drift
```

## Output

```
repo                    template_version   last_sync    zone1_hash         status
────────────────────────────────────────────────────────────────────────────────
api                     1.0.0              2026-06-01   98dfe660cbdaf240   IN_SYNC
frontend                1.0.0              2026-05-12   a3f1bc90e42d1178   DRIFTED
legacy-monolith         1.0.0              —            —                  MISSING

  1 in sync  ·  1 drifted  ·  1 missing
```

## Status values

| Status | Meaning |
|---|---|
| `IN_SYNC` | Zone 1 hash matches the current template version |
| `DRIFTED` | Zone 1 exists but hash doesn't match template |
| `NO_ZONES` | AGENTS.md exists but has no zone markers |
| `MISSING` | No AGENTS.md found in repo root or `.github/` |
| `UNKNOWN` | No schema supplied; hash computed but not compared |

## Running as a scheduled GitHub Action

```yaml
name: Drift report

on:
  schedule:
    - cron: '0 8 * * 1'   # every Monday at 8am UTC
  workflow_dispatch:

jobs:
  drift:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          repository: your-org/ai-capabilities
          sparse-checkout: drift-detector

      - name: Run drift detector
        env:
          GITHUB_TOKEN: ${{ secrets.ORG_READ_TOKEN }}
        run: |
          python drift-detector/detect-drift.py \
            --org your-org \
            --token $GITHUB_TOKEN \
            --schema https://raw.githubusercontent.com/your-org/platform-standards/main/schema.json \
            --fail-on-drift
```
